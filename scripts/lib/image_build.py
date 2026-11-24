import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from .common import (
    MANIFEST, ensure_separate, expect_hash, new_directory, require, run, sha256,
    verify_prepared, verify_stock, write, write_json,
)
from .image_formats import VendorBoot, align, le
from .module_abi import REBUILT_MODULES, kernel_exports, verify_module_abi
from .prepare import MODULE_LISTS, STUB, VENDOR_SETTINGS


MODULES = ("panel-simple.ko", "pwm_bl.ko", "edt-ft5x06.ko", "zsmalloc.ko", "zram.ko")
POLICY = "etc/selinux/precompiled_sepolicy"
BOOT0_LAYOUT = {"tiboot3.bin": 0, "tispl.bin": 0x80000, "u-boot.img": 0x280000}


def load_avb(path):
    spec = importlib.util.spec_from_file_location("crz_input_avbtool", path)
    require(spec and spec.loader, "AOSP avbtool.py 파일 경로가 필요합니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signature_key(header, blob):
    start = 256 + header.authentication_data_block_size + header.public_key_offset
    return blob[start:start + header.public_key_size]


def descriptors(items):
    result = {}
    for item in items:
        identifier = getattr(item, "partition_name", getattr(item, "key", getattr(item, "kernel_cmdline", "")))
        key = type(item).__name__, identifier
        require(key not in result, f"AVB descriptor가 중복됩니다: {key}")
        result[key] = item
    return result


def compatible_metadata(old, new, fields, label):
    for key in fields:
        require(getattr(old, key) == getattr(new, key), f"{label} 속성이 달라졌습니다: {key}")


def update_vendor_ext4(original, work, inputs, size, stage):
    fs = stage / "vendor.img"
    raw = original.read_bytes()
    data = raw[:size]
    blocks, = le("I", data, 1024 + 4)
    block_size = 1024 << le("I", data, 1024 + 24)[0]
    require(blocks * block_size == size, "vendor ext4 크기가 기존 AVB 데이터 크기와 다릅니다.")
    epoch, = le("I", data, 1024 + 48)  # ext4 superblock s_wtime
    require(epoch > 0, "순정 vendor ext4에 유효한 쓰기 시간이 없습니다.")
    ext4_env = os.environ | {
        "LC_ALL": "C", "E2FSPROGS_FAKE_TIME": str(epoch), "SOURCE_DATE_EPOCH": str(epoch),
    }
    write(fs, data)
    run("e2fsck", "-fn", fs, env=ext4_env)
    profile = MANIFEST["selinux_policy"]
    policy_inputs = []
    for path, digest in profile["inputs_sha256"].items():
        source = inputs / path
        expect_hash(source, digest)
        policy_inputs.append(source)
    policy = stage / "new.policy"
    run("secilc", "-m", "-M", "true", "-G", "-c", profile["version"], "-o", policy,
        "-f", stage / "file_contexts", *policy_inputs, work / "vendor/etc/selinux/vendor_sepolicy.cil")
    expect_hash(policy, profile["after_sha256"])

    def debug(command, modify=False):
        flags = ["-w"] if modify else []
        return run("debugfs", *flags, "-R", command, fs, cwd=stage, capture=True,
                   env=ext4_env).decode()

    for i, name in enumerate((*VENDOR_SETTINGS, POLICY, STUB)):
        target = "/" + name
        desired = policy if name == POLICY else work / "vendor" / name
        blob = desired.read_bytes()
        if name == STUB:
            uid, gid, mode = "0", "0", "0100644"
            label = b"u:object_r:vendor_configs_file:s0\0"
        else:
            stat = debug(f"stat {target}")
            perms = re.search(r"Mode:\s+0([0-7]+)", stat)
            ownership = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", stat)
            require("Type: regular" in stat and re.search(r"Links:\s+1\b", stat) and perms and ownership,
                    f"vendor 파일 메타데이터가 예상과 다릅니다: {target}")
            mode = "0" + format(int(perms.group(1), 8) | 0o100000, "o")
            uid, gid = ownership.groups()
            xattrs = re.findall(r"^\s+([\w.]+) \(\d+\)", debug(f"ea_list {target}"), re.MULTILINE)
            require(xattrs == ["security.selinux"], f"보존할 ext4 확장 속성이 예상과 다릅니다: {target}")
            debug(f"ea_get -f {i}.oldlabel {target} security.selinux")
            label = (stage / f"{i}.oldlabel").read_bytes()
            require(label.startswith(b"u:object_r:") and label.endswith(b"\0"), f"SELinux 라벨 오류: {target}")
            debug(f"rm {target}", modify=True)
        write(stage / f"{i}.new", blob)
        write(stage / f"{i}.label", label)
        debug(f"write {i}.new {target}", modify=True)
        for field, value in (("mode", mode), ("uid", uid), ("gid", gid)):
            debug(f"set_inode_field {target} {field} {value}", modify=True)
        debug(f"ea_set -f {i}.label {target} security.selinux", modify=True)
        debug(f"dump {target} {i}.read")
        debug(f"ea_get -f {i}.readlabel {target} security.selinux")
        read_stat = debug(f"stat {target}")
        read_mode = re.search(r"Mode:\s+0([0-7]+)", read_stat)
        read_owner = re.search(r"User:\s+(\d+)\s+Group:\s+(\d+)", read_stat)
        require((stage / f"{i}.read").read_bytes() == blob and
                (stage / f"{i}.readlabel").read_bytes() == label and
                read_owner and read_owner.groups() == (uid, gid) and
                read_mode and (int(read_mode.group(1), 8) | 0o100000) == int(mode, 8),
                f"vendor 파일 쓰기 후 읽기 검증 실패: {target}")
    run("e2fsck", "-fn", fs, env=ext4_env)
    changed = fs.read_bytes()
    require(len(changed) == size and changed[1116:1144] == data[1116:1144],
            "vendor ext4 크기, 기능 플래그 또는 UUID가 달라졌습니다.")
    return fs


def build_images(args):
    work = args.work_dir.resolve(strict=True)
    images = args.images.resolve(strict=True)
    modules = args.modules.resolve(strict=True)
    policy_inputs = args.policy_inputs.resolve(strict=True) if args.policy_inputs else work / "policy-inputs"
    symvers = args.module_symvers.resolve(strict=True) if args.module_symvers else None
    avbtool = args.avbtool.resolve(strict=True)
    key = args.avb_key.resolve(strict=True)
    output = args.output.resolve()
    ensure_separate(output, [work, images, modules, policy_inputs, symvers, avbtool, key])
    verify_prepared(work)
    verify_stock(images)
    for tool in ("debugfs", "e2fsck", "fec", "lz4", "openssl", "secilc"):
        require(shutil.which(tool), f"이미지 재생성에 필요한 명령이 없습니다: {tool}")
    profile = MANIFEST["reference_release"]["ramdisk_modules_sha256"]
    additions = {}
    rebuilt = {}
    exports = kernel_exports(symvers) if symvers else None
    for filename in MODULES:
        name = f"lib/modules/{filename}"
        data = (modules / filename).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != profile[name]:
            require(filename in REBUILT_MODULES and exports is not None,
                    f"모듈 SHA-256 불일치: {filename}. 재빌드 모듈은 기준 --module-symvers가 필요합니다.")
            rebuilt[filename] = verify_module_abi(data, filename, exports)
        additions[name] = data
    replacements = {name: (work / "vendor-boot-ramdisk" / name).read_bytes() for name in MODULE_LISTS}
    stock_boot = images / "vendor_boot.img"
    stock_vendor = work / "stock/vendor_a.img"
    stock_root = images / "vbmeta.img"
    avb = load_avb(avbtool)
    parser = avb.Avb()

    def parse(path):
        _, header, items, _ = parser._parse_image(avb.ImageHandler(str(path), read_only=True))
        return header, descriptors(items)

    def avb_cmd(*command):
        run(sys.executable, avbtool, *command)

    old_header, old_descriptors = parse(stock_root)
    blob = stock_root.read_bytes()
    require(old_header.algorithm_type == 2 and old_header.flags == 0 and
            old_header.public_key_metadata_size == 0 and avb.verify_vbmeta_signature(old_header, blob),
            "TI 순정 vbmeta 서명 또는 보안 플래그가 예상과 다릅니다.")
    boot_id = ("AvbHashDescriptor", "vendor_boot")
    vendor_id = ("AvbHashtreeDescriptor", "vendor")
    boot_desc, vendor_desc = old_descriptors[boot_id], old_descriptors[vendor_id]
    _, vendor_items = parse(stock_vendor)
    require(vendor_items[vendor_id].encode() == vendor_desc.encode() and
            boot_desc.flags == 0 and vendor_desc.flags == 0,
            "순정 vendor AVB descriptor가 vbmeta와 일치하지 않습니다.")

    with new_directory(output) as stage, tempfile.TemporaryDirectory(prefix=".image-build-", dir=stage) as tmp:
        temp = Path(tmp)
        public = temp / "avb.pub"
        avb_cmd("extract_public_key", "--key", key, "--output", public)
        require(public.read_bytes() == signature_key(old_header, blob),
                "지정한 AVB 키의 공개 부분이 TI 순정 vbmeta와 다릅니다.")
        boot = temp / "vendor_boot.img"
        write(boot, VendorBoot(stock_boot.read_bytes()).pack(
            (work / "dtb/crz-vendor-boot-dtb0.dtb").read_bytes(), replacements, additions,
            (work / "vendor-boot-header/cmdline.txt").read_text(encoding="ascii").removesuffix("\n"),
        ))
        avb_cmd("add_hash_footer", "--image", boot, "--partition_name", "vendor_boot",
                "--partition_size", stock_boot.stat().st_size, "--salt", boot_desc.salt.hex(),
                "--hash_algorithm", boot_desc.hash_algorithm, "--algorithm", "NONE")
        vendor = update_vendor_ext4(stock_vendor, work, policy_inputs, vendor_desc.image_size, temp)
        avb_cmd("add_hashtree_footer", "--image", vendor, "--partition_name", "vendor",
                "--partition_size", stock_vendor.stat().st_size, "--salt", vendor_desc.salt.hex(),
                "--hash_algorithm", vendor_desc.hash_algorithm, "--block_size", vendor_desc.data_block_size,
                "--fec_num_roots", vendor_desc.fec_num_roots, "--algorithm", "NONE")
        avb_cmd("verify_image", "--image", vendor)
        root = stage / "vbmeta_a.img"
        avb_cmd("make_vbmeta_image", "--output", root, "--algorithm", "SHA256_RSA4096", "--key", key,
                "--include_descriptors_from_image", stock_root, "--include_descriptors_from_image", boot,
                "--include_descriptors_from_image", vendor, "--rollback_index", old_header.rollback_index,
                "--rollback_index_location", old_header.rollback_index_location, "--flags", old_header.flags,
                "--padding_size", stock_root.stat().st_size)
        header, new_descriptors = parse(root)
        new_blob = root.read_bytes()
        require(avb.verify_vbmeta_signature(header, new_blob) and
                signature_key(header, new_blob) == signature_key(old_header, blob),
                "새 vbmeta 서명 키 또는 서명의 검증에 실패했습니다.")
        compatible_metadata(old_header, header, (
            "algorithm_type", "flags", "rollback_index", "rollback_index_location", "public_key_metadata_size",
        ), "vbmeta")
        require(old_descriptors.keys() == new_descriptors.keys(), "vbmeta descriptor 목록이 달라졌습니다.")
        for name, item in old_descriptors.items():
            if name not in (boot_id, vendor_id):
                require(item.encode() == new_descriptors[name].encode(), f"관련 없는 AVB descriptor 변경: {name}")
        compatible_metadata(boot_desc, new_descriptors[boot_id],
                            ("hash_algorithm", "partition_name", "salt", "flags"), "vendor_boot")
        compatible_metadata(vendor_desc, new_descriptors[vendor_id], (
            "dm_verity_version", "image_size", "tree_offset", "tree_size", "data_block_size",
            "hash_block_size", "fec_num_roots", "fec_offset", "fec_size", "hash_algorithm",
            "partition_name", "salt", "flags",
        ), "vendor")
        for name, path, kind in (("vendor_boot_a.img", boot, boot_id), ("vendor_a.img", vendor, vendor_id)):
            _, items = parse(path)
            require(items[kind].encode() == new_descriptors[kind].encode(), f"AVB descriptor 읽기 검증 실패: {name}")
            shutil.copyfile(path, stage / name)
        new_boot = new_descriptors[boot_id]
        digest = hashlib.new(new_boot.hash_algorithm, new_boot.salt + boot.read_bytes()[:new_boot.image_size])
        require(digest.digest() == new_boot.digest, "vendor_boot 페이로드 AVB 해시 불일치")
        require(boot.stat().st_size == stock_boot.stat().st_size and
                vendor.stat().st_size == stock_vendor.stat().st_size and len(new_blob) == len(blob),
                "이미지 파티션 크기가 달라졌습니다.")
        for name in ("boot", "init_boot", "dtbo"):
            shutil.copyfile(images / f"{name}.img", stage / f"{name}_a.img")
        outputs = {p.name: sha256(p) for p in sorted(stage.glob("*.img"))}
        write(stage / "SHA256SUMS", "".join(f"{digest}  {name}\n" for name, digest in outputs.items()).encode())
        write_json(stage / "build-report.json", {"profile": "crz-am625-gp-ti-11.00.01", "slot": "a",
                                                "images_sha256": outputs, "avb_verified": True,
                                                "rebuilt_modules_abi_imports": rebuilt})
    print(f"Android 이미지 출력: {output}")


def build_boot0(args):
    source = args.binaries.resolve(strict=True)
    base = args.base.resolve(strict=True)
    output = args.output.resolve()
    ensure_separate(output, [source, base])
    expected = MANIFEST["reference_release"]["bootloader_sha256"]
    expect_hash(base, MANIFEST["reference_release"]["boot0_base_sha256"])
    image = bytearray(base.read_bytes())
    require(len(image) == 4 * 1024 * 1024, "기준 boot0 백업 크기가 4 MiB가 아닙니다.")
    bounds = [*BOOT0_LAYOUT.values(), len(image)]
    for index, (name, offset) in enumerate(BOOT0_LAYOUT.items()):
        path = source / name
        expect_hash(path, expected[name])
        data = path.read_bytes()
        size = align(len(data), 512)
        require(offset + size <= bounds[index+1], f"boot0 범위를 넘는 구성 파일: {name}")
        image[offset:offset+size] = data + bytes(size - len(data))
    with new_directory(output) as stage:
        boot0 = stage / "boot0.img"
        write(boot0, image)
        expect_hash(boot0, expected["boot0.img"])
        for name in BOOT0_LAYOUT:
            shutil.copyfile(source / name, stage / name)
        write(stage / "SHA256SUMS", "".join(f"{expected[name]}  {name}\n"
                                             for name in ("boot0.img", *BOOT0_LAYOUT)).encode())
    print(f"검증된 boot0 구성: {output}")
