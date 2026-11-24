import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from xml.etree import ElementTree

from .common import (
    MANIFEST, MANIFEST_PATH, ROOT, STAMP, ensure_separate, expect_hash, kit_fingerprint, new_directory,
    patch, require, run, sha256, source_revision, verify_prepared, verify_stock, write, write_json,
)
from .image_formats import Ext4Text, LogicalPartition, SparseImage, VendorBoot, extract_vendor


PANEL = MANIFEST["panel_source"]["path"]
PWM = "drivers/video/backlight/pwm_bl.c"
MODULE_LISTS = ("lib/modules/modules.load", "lib/modules/modules.dep")
VENDOR_SETTINGS = (
    "etc/selinux/vendor_sepolicy.cil", "etc/ueventd.rc", "etc/audio_policy_configuration.xml",
    "etc/usb_audio_policy_configuration.xml", "etc/fstab.am62.mmc", "etc/fstab.am62.mmc.avb",
)
STUB = "etc/vintf/manifest/crz-audio-stub.xml"


def verify_repo_manifest(root):
    manifest = MANIFEST["release_manifest"]
    local = root / ".repo/local_manifests"
    require(not any(local.glob("*.xml")), f"로컬 manifest 재정의가 있습니다: {local}")
    checkout = root / ".repo/manifests"
    source_revision(checkout.resolve(), manifest["revision"])
    active = ElementTree.parse(root / ".repo/manifest.xml").getroot()
    pin = run("git", "-C", checkout, "show", f'HEAD:{manifest["android"]}', capture=True)
    if [node.get("name") for node in active.findall("include")] != [manifest["android"]]:
        require(ElementTree.tostring(active) == ElementTree.tostring(ElementTree.fromstring(pin)),
                "Android checkout에 선택된 manifest가 TI 11.00.01과 다릅니다.")
    require(active.tag == "manifest", "Android repo manifest XML 형식이 잘못됐습니다.")
    projects = {node.get("path", node.get("name")): node.get("revision")
                for node in ElementTree.fromstring(pin).findall("project")}
    for path, revision in MANIFEST["project_revisions"]["android"].items():
        require(projects.get(path) == revision, f"Android manifest 기준 SHA 불일치: {path}")
        source_revision((root / path).resolve(), revision)


def extract_members(source, target, members):
    # Materialize regular files before creating any symlink. Ubuntu's backport
    # of tarfile's data filter checks symlink targets from the archive root,
    # whereas symlink target paths are relative to the containing directory.
    links = []
    target = target.resolve()
    for member in members:
        name = Path(member.name)
        require(not name.is_absolute() and ".." not in name.parts,
                f"아카이브 상대 경로 오류: {member.name}")
        if member.issym():
            link = target / name
            destination = Path(member.linkname)
            require(not destination.is_absolute() and (link.parent / destination).resolve().is_relative_to(target),
                    f"아카이브 밖을 가리키는 심볼릭 링크: {name}")
            links.append((link, member.linkname))
        else:
            require(member.isfile() or member.isdir(), f"지원하지 않는 아카이브 항목: {name}")
            source.extract(member, target, filter="data")
    for link, destination in links:
        require(link.parent.resolve().is_relative_to(target) and
                (link.parent / destination).resolve().is_relative_to(target),
                f"아카이브 밖을 가리키는 심볼릭 링크: {link}")
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(destination)
    for link, _ in links:
        require(link.resolve().is_relative_to(target), f"아카이브 밖을 가리키는 심볼릭 링크: {link}")


def archive_project(git_root, revision, target):
    target.mkdir(parents=True)
    with subprocess.Popen(["git", "-C", str(git_root), "archive", revision],
                          stdout=subprocess.PIPE) as proc:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as source:
            extract_members(source, target, source)
        require(proc.wait() == 0, f"Git 아카이브를 읽지 못했습니다: {git_root}")


def archive_uboot(stage, git_root, archive, revision, record=None):
    tree = stage / "u-boot"
    if git_root is not None:
        archive_project(git_root, revision, tree)
    else:
        tree.mkdir()
        with tarfile.open(archive, mode="r:*") as source:
            require(source.pax_headers.get("comment") == revision, "U-Boot 아카이브 커밋이 다릅니다.")
            def members():
                for member in source.getmembers():
                    path = Path(member.name)
                    require(path.parts and path.parts[0] == "u-boot-2025.01" and ".." not in path.parts,
                            "U-Boot 아카이브에서 예상 밖 경로를 찾았습니다.")
                    if len(path.parts) > 1:
                        member.name = str(Path(*path.parts[1:]))
                        yield member

            extract_members(source, tree, members())
    return patch(tree, ROOT / "patches/u-boot/0001-crz-am625-android-boot.patch", record)


def prepare_module_sources(stage, git_root, archive, profile, record=None):
    tree = stage / "module-source"
    paths = (PANEL, PWM)
    if git_root is not None:
        for name in paths:
            write(tree / name, run("git", "-C", git_root, "show", f'HEAD:{name}', capture=True))
    else:
        with tarfile.open(archive, mode="r|*") as source:
            found = set()
            for member in source:
                name = Path(member.name).as_posix().removeprefix("android-6.12/")
                if name in paths:
                    require(member.isfile() and name not in found, f"커널 아카이브 항목 오류: {name}")
                    stream = source.extractfile(member)
                    write(tree / name, stream.read())
                    found.add(name)
            require(source.pax_headers.get("comment") == profile["revision"] and found == set(paths),
                    "커널 아카이브에 기준 커밋 또는 모듈 소스가 없습니다.")
    expect_hash(tree / PANEL, profile["before_sha256"])
    expect_hash(tree / PWM, profile["pwm_bl_sha256"])
    outputs = patch(tree, ROOT / "patches/kernel/0001-panel-simple-crz-bsd101wx1-300.patch", record)
    expect_hash(tree / PANEL, profile["after_sha256"])
    return [*outputs, tree / PWM]


def prepare_images(stage, images, record=None):
    dt_profile = MANIFEST["vendor_boot_dtb"]
    version = run("dtc", "--version", capture=True).decode().strip()
    require(version.split()[-1] == dt_profile["dtc_version"],
            f"DTS 패치는 DTC {dt_profile['dtc_version']}가 필요합니다. 현재 {version}")
    base = VendorBoot((images / "vendor_boot.img").read_bytes())
    source_dtb = stage / "dtb" / dt_profile["patch_input_filename"]
    require(hashlib.sha256(base.trees[0]).hexdigest() == dt_profile["before_sha256"],
            "순정 첫 DTB의 해시가 다릅니다.")
    write(source_dtb, run("dtc", "-q", "-I", "dtb", "-O", "dts", data=base.trees[0], capture=True))
    artifacts = patch(source_dtb.parent, ROOT / "patches/vendor-boot/0001-crz-lcd-touch-dtb.patch", record)
    patched_dtb = stage / "dtb/crz-vendor-boot-dtb0.dtb"
    write(patched_dtb, run("dtc", "-q", "-I", "dts", "-O", "dtb", source_dtb, capture=True))
    expect_hash(patched_dtb, dt_profile["after_sha256"])
    artifacts.append(patched_dtb)
    boot_header = stage / "vendor-boot-header"
    write(boot_header / "cmdline.txt", (base.cmdline + "\n").encode("ascii"))
    artifacts.extend(patch(boot_header, ROOT / "patches/vendor-boot-header/0001-crz-kernel-cmdline.patch", record))

    ramdisk = stage / "vendor-boot-ramdisk"
    for name, _, _, data in base.records():
        if name in MODULE_LISTS:
            write(ramdisk / name, data)
    require(all((ramdisk / name).is_file() for name in MODULE_LISTS), "순정 ramdisk 모듈 목록이 없습니다.")
    artifacts.extend(patch(ramdisk, ROOT / "patches/vendor-boot-ramdisk/0001-crz-module-lists.patch", record))

    original = extract_vendor(images / "super.img")
    original_file = stage / "stock/vendor_a.img"
    write(original_file, original)
    expect_hash(original_file, MANIFEST["stock_images_sha256"]["vendor_a"])
    artifacts.append(original_file)
    ext4 = Ext4Text(original)
    with (images / "super.img").open("rb") as stream:
        system = Ext4Text(LogicalPartition(SparseImage(stream), "system_a"))
        for name, digest in MANIFEST["selinux_policy"]["inputs_sha256"].items():
            if name.startswith("vendor/"):
                data = ext4.read(name.removeprefix("vendor/"))
            else:
                path = name if name.startswith("system/") else "system/" + name
                data = system.read(path)
            source = stage / "policy-inputs" / name
            write(source, data)
            expect_hash(source, digest)
            artifacts.append(source)
    vendor = stage / "vendor"
    for name in VENDOR_SETTINGS:
        write(vendor / name, ext4.read(name))
    for name in ("0001-crz-backlight.patch", "0002-crz-audio-policy.patch", "0003-crz-zram512.patch"):
        artifacts.extend(patch(vendor, ROOT / "patches/vendor" / name, record))
    try:
        ext4.read(STUB)
    except FileNotFoundError:
        addition = vendor / STUB
        write(addition, (ROOT / "overlay/vendor" / STUB).read_bytes())
        artifacts.append(addition)
    else:
        raise ValueError("순정 vendor_a에 CRZ overlay 파일이 이미 존재합니다.")
    return artifacts


def prepare(args, record=None):
    android = args.android_root.resolve(strict=True)
    require(android.is_dir(), f"Android 루트가 디렉터리가 아닙니다: {android}")
    images = args.images.resolve(strict=True) if args.images else android
    if (android / ".repo").is_dir():
        require(args.images, "AOSP 루트와 함께 --images TI_PREBUILT_DIR을 지정하세요.")
        verify_repo_manifest(android)
    else:
        require(not args.images, "--images는 .repo가 있는 Android 루트와 함께 사용하세요.")
    require(args.check or args.work_dir, "적용 시 새 --work-dir 디렉터리를 지정하세요.")
    require(shutil.which("git") and shutil.which("dtc") and shutil.which("lz4"), "git, dtc, lz4가 필요합니다.")
    uboot = args.uboot.resolve(strict=True) if args.uboot else None
    uboot_archive = args.uboot_archive.resolve(strict=True) if args.uboot_archive else None
    kernel = args.kernel.resolve(strict=True) if args.kernel else None
    kernel_archive = args.kernel_archive.resolve(strict=True) if args.kernel_archive else None
    has_uboot, has_kernel = bool(uboot or uboot_archive), bool(kernel or kernel_archive)
    if args.images_only:
        require(not has_uboot and not has_kernel, "--images-only에는 소스 옵션을 함께 지정할 수 없습니다.")
    else:
        require(has_uboot or has_kernel, "U-Boot 또는 커널 기준 소스를 지정하거나 --images-only를 사용하세요.")
        if has_uboot:
            require(hasattr(tarfile, "data_filter"), "tar data_filter를 지원하는 업데이트된 Python이 필요합니다.")
    sources = [name for name, present in (("u-boot", has_uboot), ("kernel", has_kernel)) if present]
    rev = MANIFEST["project_revisions"]["bootloader"]["u-boot"]
    panel = MANIFEST["panel_source"]
    verify_stock(images)
    if uboot:
        source_revision(uboot, rev)
    if kernel:
        source_revision(kernel, panel["revision"])
    for name, source in (("u-boot", uboot_archive), ("kernel", kernel_archive)):
        if source:
            expect_hash(source, MANIFEST["source_archives_sha256"][name])
    destination = args.work_dir.resolve() if args.work_dir else None
    if destination:
        ensure_separate(destination, [android, images, uboot, uboot_archive, kernel, kernel_archive])
        if destination.exists():
            existing = verify_prepared(destination)
            require(existing.get("sources") == sources, "기존 작업 디렉터리의 적용 범위가 다릅니다.")
            print(f"이미 적용된 작업 디렉터리: {destination}")
            return

    def populate(stage):
        artifacts = prepare_images(stage, images, record)
        if has_uboot:
            artifacts.extend(archive_uboot(stage, uboot, uboot_archive, rev, record))
        if has_kernel:
            artifacts.extend(prepare_module_sources(stage, kernel, kernel_archive, panel, record))
        write_json(stage / STAMP, {
            "manifest_sha256": sha256(MANIFEST_PATH),
            "kit_sha256": kit_fingerprint(),
            "sources": sources,
            "artifacts": {path.relative_to(stage).as_posix(): sha256(path) for path in artifacts},
        })

    if args.check:
        with tempfile.TemporaryDirectory(prefix="crz-check-") as tmp:
            populate(Path(tmp))
        print("사전 검사 성공. 입력 파일과 작업 디렉터리에 변경 사항을 저장하지 않았습니다.")
    else:
        with new_directory(destination) as stage:
            populate(stage)
        print(f"적용된 작업 사본: {destination}")
