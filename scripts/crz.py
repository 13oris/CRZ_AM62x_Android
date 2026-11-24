#!/usr/bin/env python3
"""Entry point for the CRZ AM625 porting kit."""

import argparse
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
from xml.etree import ElementTree

from lib.device import PARTITIONS, flash_boot0, flash_fastboot, flash_sd, verify_adb, verify_images, verify_uart
from lib.image_build import build_boot0, build_images
from lib.prepare import prepare
from lib.source_build import build_modules, build_uboot


def prepare_parser():
    p = argparse.ArgumentParser(prog="apply_change.sh", description="TI 11.00.01 입력을 확인하고 별도 작업 사본에 CRZ 변경을 적용합니다.")
    p.add_argument("android_root", type=Path, metavar="TI_IMAGE_DIR_OR_AOSP_ROOT")
    p.add_argument("--images", type=Path, help="AOSP 루트를 지정할 때 사용할 TI 순정 이미지 디렉터리")
    p.add_argument("--work-dir", type=Path, help="패치 작업 사본을 저장할 새 디렉터리")
    p.add_argument("--check", "--dry-run", action="store_true", help="임시 사본에서만 적용 검사")
    p.add_argument("--images-only", action="store_true", help="Android 이미지 준비 항목만 적용")
    uboot = p.add_mutually_exclusive_group()
    uboot.add_argument("--uboot", type=Path, help="TI 기준 SHA의 U-Boot Git 루트")
    uboot.add_argument("--uboot-archive", type=Path, help="기준 TI U-Boot 소스 아카이브")
    kernel = p.add_mutually_exclusive_group()
    kernel.add_argument("--kernel", type=Path, help="e9a61e5 커널 Git 루트")
    kernel.add_argument("--kernel-archive", type=Path, help="기준 TI 커널 소스 아카이브")
    p.set_defaults(action=prepare)
    return p


def path_options(parser, *names):
    for name in names:
        parser.add_argument(f"--{name}", type=Path, required=True)


def build_parser():
    p = argparse.ArgumentParser(prog="scripts/build.sh", description="준비된 입력에서 CRZ 빌드 산출물을 생성합니다.")
    commands = p.add_subparsers(dest="profile", required=True)
    images = commands.add_parser("images", help="vendor_boot, vendor, vbmeta와 슬롯 A 이미지 묶음 재생성")
    path_options(images, "work-dir", "images", "modules", "avbtool", "avb-key", "output")
    images.add_argument("--policy-inputs", type=Path, help="별도로 추출한 정책 입력. 기본은 준비 디렉터리의 순정 파일.")
    images.add_argument("--module-symvers", type=Path, help="재빌드 패널·PWM 모듈에 필요한 기준 ABI export CRC 목록")
    images.set_defaults(action=build_images)
    uboot = commands.add_parser("uboot", help="Linux에서 TI 빌드 절차로 CRZ GP 부트로더 빌드")
    path_options(uboot, "work-dir", "ti-bootloader-root", "output")
    uboot.add_argument("--native-toolchains", action="store_true", help="호스트의 GNU ARM/AArch64 교차 도구 사용")
    uboot.set_defaults(action=build_uboot)
    modules = commands.add_parser("modules", help="정확한 SDK 커널 ABI로 LCD 외부 모듈 빌드")
    path_options(modules, "work-dir", "kernel-tree", "kernel-out", "headers", "llvm-bin", "output")
    modules.add_argument("--native-libs", type=Path, help="기존 aarch64 VM 빌드의 호스트 라이브러리 sysroot")
    modules.add_argument("--jobs", type=int, default=2)
    modules.set_defaults(action=build_modules)
    boot0 = commands.add_parser("boot0", help="검증된 릴리스 부트로더 세 파일을 boot0 이미지로 조합")
    path_options(boot0, "binaries", "base", "output")
    boot0.set_defaults(action=build_boot0)
    return p


def flash_parser():
    p = argparse.ArgumentParser(prog="scripts/flash.sh",
                                description="대상을 검사합니다. 실제 쓰기는 --write와 대상별 --confirm 값이 필요합니다.")
    commands = p.add_subparsers(dest="profile", required=True)
    sd = commands.add_parser("sd", help="기존 SD FAT 파티션에 해시를 확인한 U-Boot 파일 3개 설치")
    path_options(sd, "binaries", "mount")
    sd.set_defaults(action=flash_sd)
    fastboot = commands.add_parser("fastboot", help="지정한 슬롯 A 파티션 하나에 이미지 적용")
    path_options(fastboot, "images")
    fastboot.add_argument("--serial", required=True)
    fastboot.add_argument("--partition", choices=PARTITIONS, required=True)
    fastboot.set_defaults(action=flash_fastboot)
    boot0 = commands.add_parser("boot0", help="CRZ 보드의 SD 복구 Linux에서 4 MiB eMMC boot0 쓰기")
    path_options(boot0, "device", "image", "backup")
    boot0.set_defaults(action=flash_boot0)
    for sub in (sd, fastboot, boot0):
        sub.add_argument("--write", action="store_true", help="사전 검사를 통과한 대상에 쓰기")
        sub.add_argument("--confirm", help="사전 검사에서 출력한 정확한 승인 문자열")
    return p


def verify_parser():
    p = argparse.ArgumentParser(prog="scripts/verify.sh", description="이미지 묶음, ADB 장치 또는 UART 로그를 확인합니다.")
    commands = p.add_subparsers(dest="profile", required=True)
    images = commands.add_parser("images", help="릴리스 또는 재생성 이미지의 SHA-256 확인")
    path_options(images, "images")
    images.set_defaults(action=verify_images)
    adb = commands.add_parser("adb", help="연결된 Android 장치의 부팅 완료, 커널, FBE, SELinux, zram 확인")
    adb.add_argument("--serial", required=True)
    adb.add_argument("--with-su", action="store_true", help="userdebug su로 제한된 zram 크기만 읽기")
    adb.set_defaults(action=verify_adb)
    uart = commands.add_parser("uart", help="저장된 로그에서 보드, 커널, 부팅 완료 확인")
    path_options(uart, "log")
    uart.set_defaults(action=verify_uart)
    return p


def main():
    parsers = {"prepare": prepare_parser, "build": build_parser, "flash": flash_parser, "verify": verify_parser}
    if len(sys.argv) < 2 or sys.argv[1] not in parsers:
        print("apply_change.sh 또는 scripts/{build,flash,verify}.sh를 사용하세요.", file=sys.stderr)
        return 2
    args = parsers[sys.argv[1]]().parse_args(sys.argv[2:])
    try:
        args.action(args)
    except (ValueError, OSError, KeyError, AttributeError, struct.error, subprocess.CalledProcessError,
            tarfile.TarError, ElementTree.ParseError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            # Keep any key paths and external argument values out of error summaries.
            message = f"{Path(exc.cmd[0]).name} 종료 코드 {exc.returncode}"
        else:
            message = str(exc)
        print(f"오류: {message}", file=sys.stderr)
        if sys.argv[1] == "prepare":
            print("원본에는 적용하지 않았습니다. 입력·출력 경로를 확인한 뒤 --check로 다시 검사하세요.", file=sys.stderr)
        elif sys.argv[1] == "flash" and args.write:
            print("쓰기가 시작됐으면 부분 적용 가능성이 있습니다. 재부팅 전 대상 상태와 백업을 확인하세요.",
                  file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("중단했습니다. 쓰기 중이었다면 대상 상태와 백업을 확인하세요.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
