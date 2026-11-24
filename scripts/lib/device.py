import json
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

from .common import MANIFEST, expect_hash, require, run
from .image_build import BOOT0_LAYOUT


PROFILE = "crz-am625-gp-ti-11.00.01"
PARTITIONS = {
    "vendor_boot_a": 33554432,
    "vendor_a": 96776192,
    "vbmeta_a": 65536,
}


def image_hashes(directory):
    reference = MANIFEST["reference_release"]["android_sha256"]
    report = directory / "build-report.json"
    if not report.is_file():
        recorded = reference
    else:
        value = json.loads(report.read_text(encoding="utf-8"))
        require(value.get("profile") == PROFILE and value.get("slot") == "a" and
                value.get("avb_verified") is True, "CRZ 이미지의 AVB 검증 기록이 필요합니다.")
        recorded = value["images_sha256"]
        require(set(recorded) == set(reference), "CRZ 이미지 세트가 불완전합니다.")
        for name in ("boot_a.img", "init_boot_a.img", "dtbo_a.img"):
            require(recorded[name] == reference[name], f"TI 순정 이미지를 유지해야 합니다: {name}")
    for name, digest in recorded.items():
        require(re.fullmatch(r"[0-9a-f]{64}", digest), f"잘못된 이미지 SHA-256: {name}")
        expect_hash(directory / name, digest)
    return recorded


def confirm(args, token):
    print(f"쓰기 승인 문자열: {token}")
    if not args.write:
        print("사전 검사만 수행했습니다. 쓰기에는 --write와 정확한 --confirm 값이 모두 필요합니다.")
        return False
    require(args.confirm == token, "승인 문자열이 일치하지 않아 쓰기를 중단합니다.")
    return True


def output(*args):
    return run(*args, capture=True).decode().strip()


def mmc_type(name):
    path = Path("/sys/class/block") / name / "device/type"
    return path.read_text().strip() if path.is_file() else ""


def sd_target(mount):
    device = output("findmnt", "-n", "-o", "SOURCE", "--mountpoint", mount)
    fstype = output("findmnt", "-n", "-o", "FSTYPE", "--mountpoint", mount)
    options = output("findmnt", "-n", "-o", "OPTIONS", "--mountpoint", mount).split(",")
    require(device.startswith("/dev/") and fstype in ("vfat", "msdos") and "rw" in options,
            "읽기/쓰기로 마운트한 SD FAT 파티션 경로가 필요합니다.")
    require(output("lsblk", "-dn", "-o", "TYPE", device) == "part", "SD FAT 파티션이 필요합니다.")
    parent = output("lsblk", "-dn", "-o", "PKNAME", device)
    require(parent and (mmc_type(parent) == "SD" or
                        (mmc_type(parent) != "MMC" and output("lsblk", "-dn", "-o", "RM", "/dev/" + parent) == "1")),
            "대상 디스크를 이동식 SD로 확인할 수 없습니다.")
    return device


def flash_sd(args):
    require(platform.system() == "Linux", "SD 대상 확인은 Linux에서 실행하세요.")
    source = args.binaries.resolve(strict=True)
    mount = args.mount.resolve(strict=True)
    require(mount.is_dir(), "정확한 SD 마운트 지점이 필요합니다.")
    for name in BOOT0_LAYOUT:
        expect_hash(source / name, MANIFEST["reference_release"]["bootloader_sha256"][name])
    device = sd_target(mount)
    print(output("lsblk", "-o", "NAME,TYPE,SIZE,RM,TRAN,MODEL,MOUNTPOINTS", device))
    if not confirm(args, f"SD:{device}"):
        return
    for name in BOOT0_LAYOUT:
        require(sd_target(mount) == device, "처음 확인한 SD 장치가 바뀌었습니다.")
        target = mount / name
        require(not target.is_symlink() and (not target.exists() or target.is_file()), f"잘못된 FAT 대상: {target}")
        with tempfile.NamedTemporaryFile(prefix=".crz-", dir=mount, delete=False) as tmp:
            stage = Path(tmp.name)
            try:
                with (source / name).open("rb") as src:
                    shutil.copyfileobj(src, tmp)
                tmp.flush()
                os.fsync(tmp.fileno())
                expect_hash(stage, MANIFEST["reference_release"]["bootloader_sha256"][name])
                require(sd_target(mount) == device, "쓰기 직전 SD 장치가 바뀌었습니다.")
                stage.replace(target)
                expect_hash(target, MANIFEST["reference_release"]["bootloader_sha256"][name])
            finally:
                stage.unlink(missing_ok=True)
    run("sync")
    print("SD FAT의 U-Boot 구성 파일 3개를 쓰고 읽기 검증했습니다.")


def fastboot_getvar(serial, name):
    completed = subprocess.run(["fastboot", "-s", serial, "getvar", name], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in completed.stdout.splitlines():
        match = re.fullmatch(r"(?:\(bootloader\)\s*)?" + re.escape(name) + r":\s*(\S+)\s*", line)
        if match:
            return match.group(1)
    raise ValueError(f"fastboot에서 {name} 확인 결과가 없습니다.")


def flash_fastboot(args):
    serial = args.serial
    require(re.fullmatch(r"[A-Za-z0-9_.:-]+", serial), "fastboot serial 형식이 잘못됐습니다.")
    directory = args.images.resolve(strict=True)
    hashes = image_hashes(directory)
    partition = args.partition
    image = directory / f"{partition}.img"

    def target():
        matches = [line.split()[0] for line in output("fastboot", "devices").splitlines()
                   if len(line.split()) >= 2 and line.split()[1] == "fastboot"]
        require(matches.count(serial) == 1, f"지정한 fastboot 장치를 확인할 수 없습니다: {serial}")
        require(fastboot_getvar(serial, "current-slot").removeprefix("_") == "a",
                "기존 CRZ 설치의 활성 슬롯 A가 확인되어야 합니다.")
        size = int(fastboot_getvar(serial, f"partition-size:{partition}"), 0)
        require(size == PARTITIONS[partition] == image.stat().st_size,
                f"파티션과 이미지 크기가 일치하지 않습니다: {partition} ({size})")
        if partition == "vendor_a":
            require(fastboot_getvar(serial, "is-userspace") == "yes" and
                    fastboot_getvar(serial, "is-logical:vendor_a") == "yes",
                    "vendor_a는 확인된 fastbootd 논리 파티션에만 적용할 수 있습니다.")

    target()
    print(f"fastboot 대상 {serial}, {partition}, {image.stat().st_size} bytes")
    if not confirm(args, f"FASTBOOT:{serial}:{partition}"):
        return
    target()
    expect_hash(image, hashes[image.name])
    if partition == "vbmeta_a":
        print("같은 묶음의 vendor_boot_a 및 vendor_a 적용을 확인한 뒤 재부팅하세요.")
    run("fastboot", "-s", serial, "flash", partition, image)
    print("fastboot 쓰기 응답을 확인했습니다. 저장장치 직접 읽기 검증은 별도로 수행하세요.")


def boot0_target(device):
    require(re.fullmatch(r"/dev/mmcblk[0-9]+boot0", str(device)) and device.is_block_device(),
            "명시적인 /dev/mmcblkNboot0 블록 장치가 필요합니다.")
    name = device.name
    emmc = name.removesuffix("boot0")
    require(mmc_type(emmc) == "MMC", "대상 eMMC를 확인할 수 없습니다.")
    root = output("findmnt", "-n", "-o", "SOURCE", "--mountpoint", "/")
    sd = re.fullmatch(r"/dev/(mmcblk[0-9]+)p[0-9]+", root)
    require(sd and sd.group(1) != emmc and mmc_type(sd.group(1)) == "SD",
            "CRZ 보드의 SD 복구 Linux에서만 boot0를 쓸 수 있습니다.")
    disk = Path("/dev") / emmc
    mounts = output("lsblk", "-nr", "-o", "MOUNTPOINTS", disk)
    require(not mounts, f"eMMC에 마운트된 영역이 있습니다: {disk}")
    for path in Path("/sys/class/block").glob(emmc + "*"):
        if re.fullmatch(re.escape(emmc) + r"(?:p[0-9]+|boot[01]|rpmb)?", path.name):
            require(not any((path / "holders").glob("*")), f"eMMC 사용 중: {path.name}")
            require(not output("lsblk", "-dn", "-o", "MOUNTPOINTS", Path("/dev") / path.name),
                    f"eMMC에 마운트된 영역이 있습니다: {path.name}")
    require(output("blockdev", "--getsize64", device) == "4194304", "boot0 용량이 4 MiB가 아닙니다.")
    force_ro = Path("/sys/class/block") / name / "force_ro"
    require(force_ro.read_text().strip() == "1", "boot0의 쓰기 보호가 활성화된 상태에서 시작해야 합니다.")
    return force_ro


def flash_boot0(args):
    require(platform.system() == "Linux", "boot0 작업에는 Linux가 필요합니다.")
    device = args.device
    image = args.image.resolve(strict=True)
    target = image.read_bytes()
    require(hashlib.sha256(target).hexdigest() == MANIFEST["reference_release"]["bootloader_sha256"]["boot0.img"],
            "검증된 4 MiB CRZ boot0 이미지가 필요합니다.")
    args.backup = args.backup.absolute()
    require(args.backup.parent.is_dir() and not args.backup.exists() and not args.backup.is_symlink(),
            "신규 boot0 백업 파일 경로가 필요합니다.")
    require(not args.backup.resolve().is_relative_to(Path("/dev")) and
            not args.backup.resolve().is_relative_to(Path("/sys")) and
            not args.backup.resolve().is_relative_to(Path("/proc")), "백업은 일반 파일 경로를 사용하세요.")
    boot0_target(device)
    print(f"eMMC boot0 대상 {device}, 원본 백업 {args.backup}")
    if not confirm(args, f"BOOT0:{device}"):
        return
    require(os.geteuid() == 0, "boot0 쓰기는 SD 복구 Linux에서 관리자 권한으로 실행하세요.")
    force_ro = boot0_target(device)
    with device.open("rb") as handle:
        original = handle.read(4194304)
    require(len(original) == 4194304, "기존 boot0의 전체 읽기에 실패했습니다.")
    if original == target:
        print("이미 같은 boot0가 적용되어 있습니다.")
        return
    fd = os.open(args.backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(original)
        handle.flush()
        os.fsync(handle.fileno())
    require(args.backup.read_bytes() == original, "boot0 백업 읽기 검증에 실패했습니다.")
    boot0_target(device)
    try:
        force_ro.write_text("0\n")
        with device.open("r+b") as handle:
            require(handle.write(target) == len(target), "boot0 부분 쓰기")
            handle.flush()
            os.fsync(handle.fileno())
        with device.open("rb") as handle:
            require(handle.read(len(target)) == target, f"boot0 읽기 검증 실패. 백업: {args.backup}")
    finally:
        force_ro.write_text("1\n")
    require(force_ro.read_text().strip() == "1", "boot0 쓰기 보호를 복구하지 못했습니다.")
    print(f"boot0 전체 읽기 검증과 쓰기 보호 복구 성공. 백업: {args.backup}")


def verify_images(args):
    directory = args.images.resolve(strict=True)
    for name, digest in image_hashes(directory).items():
        print(f"OK  {name}  {digest}")


def verify_adb(args):
    serial = args.serial
    require(re.fullmatch(r"[A-Za-z0-9_.:-]+", serial), "ADB serial 형식이 잘못됐습니다.")
    require(output("adb", "-s", serial, "get-state") == "device", "ADB 장치가 준비되지 않았습니다.")
    expected = {
        ("getprop", "sys.boot_completed"): "1",
        ("getprop", "ro.build.version.release"): "16",
        ("getprop", "ro.boot.slot_suffix"): "_a",
        ("getprop", "ro.crypto.state"): "encrypted",
        ("getenforce",): "Enforcing",
        ("uname", "-r"): MANIFEST["reference_release"]["running_kernel"],
        ("cat", "/sys/block/zram0/disksize"): "536870912",
    }
    failures = []
    for command, want in expected.items():
        result = subprocess.run(["adb", "-s", serial, "shell", *command], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        value = result.stdout.strip()
        passed = not result.returncode and value == want
        print(f"{'OK' if passed else 'FAIL'}  {' '.join(command)}  {value or '(값 없음)'}")
        if not passed:
            failures.append(" ".join(command))
    require(not failures, "장치 확인 실패 또는 권한 미확인: " + ", ".join(failures))


def verify_uart(args):
    text = args.log.read_text(errors="replace")
    tests = {
        "U-Boot 2025.01": r"U-Boot(?: SPL)? 2025\.01",
        "CRZ AM625": r"CRZ AM62(?:5|X)",
        "Android 커널": r"Linux version 6\.12\.23-android16-5-gaf4cb0e2168b-4k",
        "Android 부팅 완료": r"(?:sys\.boot_completed=1|(?:getprop sys\.boot_completed)\s*\n1\b)",
    }
    missing = []
    for name, pattern in tests.items():
        found = bool(re.search(pattern, text, re.IGNORECASE))
        print(f"{'OK' if found else '미확인'}  {name}")
        if not found:
            missing.append(name)
    require(not missing, "UART 로그에 필요한 증거가 없습니다: " + ", ".join(missing))
