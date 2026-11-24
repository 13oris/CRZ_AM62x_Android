import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile

from .common import (
    MANIFEST, ensure_separate, expect_hash, new_directory, require, run, sha256,
    source_revision, verify_prepared, write, write_json,
)
from .module_abi import kernel_exports, verify_module_abi
from .prepare import PANEL, PWM, archive_project


def build_uboot(args):
    work = args.work_dir.resolve(strict=True)
    sdk = args.ti_bootloader_root.resolve(strict=True)
    output = args.output.resolve()
    ensure_separate(output, [work, sdk])
    state = verify_prepared(work)
    require("u-boot" in state.get("sources", []), "U-Boot 소스가 포함된 작업 디렉터리가 필요합니다.")
    require(platform.system() == "Linux" and platform.machine() == "x86_64",
            "TI 공식 부트로더 빌드의 기본 툴체인은 x86_64 Linux용입니다.")
    require(hasattr(tarfile, "data_filter"), "tar data_filter를 지원하는 Python이 필요합니다.")
    revisions = MANIFEST["project_revisions"]["bootloader"]
    for name, revision in revisions.items():
        if name != "u-boot":
            source_revision((sdk / name).resolve(strict=True), revision)
    with new_directory(output) as stage, tempfile.TemporaryDirectory(prefix=".ti-build-", dir=stage) as temp:
        kit = Path(temp)
        for name, revision in revisions.items():
            if name == "u-boot":
                shutil.copytree(work / name, kit / name, symlinks=True)
            else:
                archive_project(sdk / name, revision, kit / name)
        environment = os.environ.copy()
        environment.pop("SYSTEM_WIDE_TOOLCHAINS", None)
        run("bash", "./build/build_all.sh", "--config=build/config/boards/am62x-sk.yaml",
            cwd=kit, env=environment)
        built = kit / "out/am62x-sk/release"
        names = {
            "tiboot3-release-gp.bin": "tiboot3.bin",
            "tispl-release.bin": "tispl.bin",
            "u-boot-release.img": "u-boot.img",
        }
        actual = {}
        for source, name in names.items():
            shutil.copyfile(built / source, stage / name)
            actual[name] = sha256(stage / name)
        expected = MANIFEST["reference_release"]["bootloader_sha256"]
        write_json(stage / "build-report.json", {
            "recipe": "TI build_all.sh am62x-sk, CRZ patched U-Boot",
            "sha256": actual,
            "matches_reference": {k: v == expected[k] for k, v in actual.items()},
        })
    print(f"U-Boot 빌드 출력: {output}")


def build_modules(args):
    work = args.work_dir.resolve(strict=True)
    source = args.kernel_tree.resolve(strict=True)
    abi = args.kernel_out.resolve(strict=True)
    headers = args.headers.resolve(strict=True)
    llvm = args.llvm_bin.resolve(strict=True)
    libs = args.native_libs.resolve(strict=True) if args.native_libs else None
    output = args.output.resolve()
    ensure_separate(output, [work, source, abi, headers, llvm, libs])
    require(platform.system() == "Linux", "커널 모듈 빌드에는 Linux 환경이 필요합니다.")
    state = verify_prepared(work)
    require("kernel" in state.get("sources", []), "패널 모듈 소스가 포함된 작업 디렉터리가 필요합니다.")
    profile = MANIFEST["module_build_abi"]
    expect_hash(abi / ".config", profile["config_sha256"])
    exports = kernel_exports(abi / "Module.symvers")
    panel = MANIFEST["panel_source"]
    expect_hash(source / PANEL, panel["before_sha256"])
    expect_hash(source / PWM, panel["pwm_bl_sha256"])
    clang = run(llvm / "clang", "--version", capture=True).decode()
    require(profile["clang_release"] in clang or "19.0.1" in clang,
            "기준 Android Clang r536225 (19.0.1)가 필요합니다.")
    require(args.jobs > 0, "--jobs는 양수여야 합니다.")
    with new_directory(output) as stage, tempfile.TemporaryDirectory(prefix=".module-build-", dir=stage) as temp:
        private = Path(temp)
        tree, out, module_dir = (private / name for name in ("kernel", "out", "modules"))
        shutil.copytree(source, tree, symlinks=True, ignore=shutil.ignore_patterns(".git", "build-crz", "__pycache__"))
        shutil.copytree(abi, out, symlinks=True)
        require(not (out / "Makefile").is_symlink(), "O= Makefile이 심볼릭 링크입니다.")
        link = out / "source"
        if link.is_symlink():
            link.unlink()
        require(not link.exists(), "O= 사본에 예상 밖 source 항목이 있습니다.")
        link.symlink_to(tree, target_is_directory=True)
        # The recorded O= directory was generated against an absolute kernel source path.
        for path in [out / "Makefile", *out.rglob("*.cmd")]:
            require(not path.is_symlink(), f"O= 사본에 예상 밖 빌드 메타데이터 링크: {path}")
            if path.is_file():
                data = path.read_bytes().replace(str(source).encode(), str(tree).encode())
                path.write_bytes(data.replace(str(abi).encode(), str(out).encode()))
        for folder in (tree, out):
            for path in folder.rglob("*"):
                require(not path.is_symlink() or path.resolve().is_relative_to(private),
                        f"빌드 사본 밖을 가리키는 링크: {path}")
        module_dir.mkdir()
        for name in (PANEL, PWM):
            shutil.copyfile(work / "module-source" / name, module_dir / name.split("/")[-1])
        write(module_dir / "Makefile", b"obj-m += panel-simple.o\nobj-m += pwm_bl.o\n")
        includes = [
            headers / "arch/arm64/include", out / "arch/arm64/include/generated",
            headers / "include", out / "include", headers / "arch/arm64/include/uapi",
            out / "arch/arm64/include/generated/uapi", headers / "include/uapi", out / "include/generated/uapi",
        ]
        include_flags = [f"-I{path}" for path in includes] + [
            f"-include {headers}/include/linux/compiler-version.h",
            f"-include {headers}/include/linux/kconfig.h",
        ]
        tool_names = {
            "CC": "clang", "LD": "ld.lld", "AR": "llvm-ar", "NM": "llvm-nm",
            "OBJCOPY": "llvm-objcopy", "OBJDUMP": "llvm-objdump", "STRIP": "llvm-strip",
        }
        options = [f"{name}={llvm / tool}" for name, tool in tool_names.items()]
        if libs:
            libdir = libs / "usr/lib/aarch64-linux-gnu"
            options.extend([f"HOSTCFLAGS=-I{libs}/usr/include", f"HOSTLDFLAGS=-L{libdir} -Wl,-rpath,{libdir}"])
        paths = [*includes, llvm, module_dir, tree]
        if libs:
            paths.append(libs)
        require(not any(any(c.isspace() for c in str(path)) for path in paths),
                "Kbuild와 기록된 도구 래퍼를 위해 경로에 공백이 없는 위치를 사용하세요.")
        run("make", "-C", tree, f"O={out}", f"M={module_dir}", "ARCH=arm64",
            "CROSS_COMPILE=aarch64-linux-gnu-", *options, "READELF=aarch64-linux-gnu-readelf",
            "HOSTCC=gcc", "HOSTCXX=g++", "LINUXINCLUDE=" + " ".join(include_flags),
            f"-j{args.jobs}", "modules")
        expect_hash(out / ".config", profile["config_sha256"])
        expected = MANIFEST["reference_release"]["ramdisk_modules_sha256"]
        results = {}
        for name in ("panel-simple.ko", "pwm_bl.ko"):
            shutil.copyfile(module_dir / name, stage / name)
            digest = sha256(stage / name)
            checked = verify_module_abi((stage / name).read_bytes(), name, exports)
            results[name] = {"sha256": digest, "abi_imports_verified": checked,
                             "matches_reference": digest == expected[f"lib/modules/{name}"]}
        write_json(stage / "build-report.json", results)
    print(f"커널 모듈 출력: {output}")
