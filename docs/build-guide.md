# 패치 적용과 빌드

## 작업 사본 준비

- `TI_IMAGES`는 TI 11.00.01 eMMC userdebug 배포본을 푼 디렉터리입니다. `CRZ_WORK`와 빌드 출력은 이 Git 저장소 및 입력 트리 외부의 신규 경로를 지정합니다.
- 소스 아카이브 방식은 [manifest](../manifest/ti-11.00.01.json)의 SHA-256과 아카이브 내 Git revision을 확인합니다. Git 체크아웃 방식은 정확한 HEAD에서 파일을 추출하므로 현재 로컬 작업 변경이 섞이지 않습니다.

```sh
./apply_change.sh --check \
  --uboot-archive "$TI_UBOOT_ARCHIVE" --kernel-archive "$TI_KERNEL_ARCHIVE" "$TI_IMAGES"

./apply_change.sh --work-dir "$CRZ_WORK" \
  --uboot-archive "$TI_UBOOT_ARCHIVE" --kernel-archive "$TI_KERNEL_ARCHIVE" "$TI_IMAGES"
```

위 변수에는 각각 `AM62x_11.00.01_Uboot_ef2eb76b65.tgz`와 `AM62x_11.00.01_Kernel_e9a61e5d36.tar`를 지정합니다. Git 방식은 `--uboot`와 `--kernel`을 사용합니다. 한 소스만 필요한 경우 해당 소스 옵션만 전달할 수 있습니다. Android 이미지 입력만 준비하려면 `--images-only`를 사용합니다. AOSP 소스 루트에 `--images "$TI_IMAGES"`를 함께 넘기면 선택된 Android manifest와 관련 프로젝트 SHA도 검사합니다.

출력에는 `u-boot/` 소스 사본과 `module-source/`의 두 모듈 소스, `dtb/`, vendor boot 헤더·ramdisk 텍스트, `vendor/` 설정, 추출된 `stock/vendor_a.img` 및 `policy-inputs/`가 포함됩니다. 순정 파일을 담은 이 디렉터리는 빌드 작업용입니다. 적용은 임시 작업 디렉터리에서 끝까지 검사한 뒤 한 번에 공개합니다. 같은 작업 경로로 재실행하면 준비 기록과 출력 파일 해시를 확인합니다. 변경되었거나 앞선 버전의 준비 디렉터리는 보존하고 새 경로를 지정하세요.

## U-Boot

```sh
./scripts/build.sh uboot --work-dir "$CRZ_WORK" \
  --ti-bootloader-root "$TI_BOOTLOADER_ROOT" --output "$CRZ_UBOOT_OUT"
```

이 명령은 TI bootloader manifest에서 `build`, 펌웨어, TF-A, OP-TEE와 TA 프로젝트의 SHA를 확인하고 별도 빌드 사본을 준비합니다. TI의 `build/build_all.sh --config=build/config/boards/am62x-sk.yaml`이 CRZ 패치가 반영된 A53/R5 defconfig를 사용합니다. GP `tiboot3.bin`, `tispl.bin`, `u-boot.img`와 해시 비교 보고서를 출력합니다.

Ubuntu aarch64에서 실행할 때는 기존 GNU ARM 및 AArch64 교차 도구를 PATH에 두고 `--native-toolchains`를 추가합니다. GCC 11.4.0, TI 기준 프로젝트 7개와 TI 빌드 의존성을 사용해 전체 체인 빌드를 검증했습니다. 출력은 기존 실기 배포본과 해시가 달라 SD 부팅에서 별도로 확인해야 합니다. [검증 결과와 산출물 해시](verification.md#부트로더)

과거 작업 VM에서 저장된 CRZ A53 빌드 명령은 `make O=build-a53-android CROSS_COMPILE=aarch64-linux-gnu- -j4`이고, 해당 출력 디렉터리에 미리 준비된 Android `.config`가 있었습니다. 당시 R5 GP `tiboot3.bin`과 A53 `u-boot.img`는 릴리스와 일치합니다. 릴리스 `tispl.bin`은 별도로 보존한 당시 파일과 일치했으며 현재 VM 빌드 출력과 다릅니다. [TI AM62x 부트로더 빌드](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/android/Foundational_Components_Bootloaders.html)

## 커널 모듈

```sh
./scripts/build.sh modules --work-dir "$CRZ_WORK" \
  --kernel-tree "$TI_KERNEL_TREE" --kernel-out "$TI_KERNEL_OUT" \
  --headers "$TI_KERNEL_HEADERS" --llvm-bin "$ANDROID_LLVM_BIN" \
  --output "$CRZ_MODULE_OUT"
```

`TI_KERNEL_TREE`에는 `e9a61e5` 소스를 준비합니다. `TI_KERNEL_OUT`은 실제 Android GKI ABI의 `.config`, `Module.symvers`, 생성 헤더와 Kbuild 산출물을 가진 O= 디렉터리입니다. `TI_KERNEL_HEADERS`에는 해당 SDK의 헤더 트리를 지정합니다. `ANDROID_LLVM_BIN`에는 Clang r536225 도구 디렉터리 또는 기존 QEMU 래퍼 디렉터리를 사용합니다. 기존 aarch64 VM의 호스트 라이브러리를 재사용하려면 `--native-libs`를 지정합니다.

빌드 명령은 별도 복사본에서 `make -C … O=… M=… ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- … modules`를 실행합니다. 출력은 `panel-simple.ko`, `pwm_bl.ko`, ABI 검증 수와 릴리스 해시 비교입니다. Ubuntu VM에서 두 모듈을 재컴파일했고 해당 SDK의 import CRC를 각각 57개, 26개 검증했습니다. 모듈 전체 해시는 기존 배포본과 달랐습니다. 새로 빌드한 모듈의 보드 로드는 미검증입니다.

## Android 이미지

```sh
./scripts/build.sh images --work-dir "$CRZ_WORK" --images "$TI_IMAGES" \
  --modules "$CRZ_MODULES" \
  --avbtool "$AVBTOOL_PY" --avb-key "$TI_AVB_KEY_FILE" --output "$CRZ_IMAGES_OUT"

./scripts/verify.sh images --images "$CRZ_IMAGES_OUT"
```

- `CRZ_MODULES`에는 모듈 5개를 준비합니다. `edt-ft5x06.ko`, `zram.ko`, `zsmalloc.ko`는 TI `device/ti/am62x-kernel` 프로젝트의 `kernel/6.12/`에서 가져오며 기준 해시가 일치해야 합니다. 새 패널·PWM 모듈을 사용할 때는 `--module-symvers "$TI_KERNEL_OUT/Module.symvers"`를 추가합니다. 이미지 빌드 전에 ARM64 모듈 형식, vermagic, 모듈명, 종속성, 패널 alias 및 import CRC를 확인합니다.
- 스크립트는 순정 `super.img`에서 추출하고 SHA-256을 확인한 CIL 파일을 사용합니다. 같은 입력을 별도 경로에 이미 준비했다면 `--policy-inputs`로 지정할 수 있습니다. 정책 컴파일은 기존 작업과 같은 `secilc -m -M true -G -c 30`을 사용합니다. [정책 입력 경로와 해시](../manifest/ti-11.00.01.json)
- `TI_AVB_KEY_FILE`은 해당 TI 개발 배포본이 신뢰하는 AVB 서명 키 경로입니다. 스크립트는 공개 부분이 순정 `vbmeta.img`와 일치하는지 확인하고 키 파일은 작업 산출물에 넣지 않습니다. 정책과 입력이 일치하고 AVB 서명·descriptor 검증이 끝나야 최종 출력이 생깁니다.
- 출력은 `boot_a.img`, `init_boot_a.img`, `dtbo_a.img`, `vendor_boot_a.img`, `vendor_a.img`, `vbmeta_a.img`, `SHA256SUMS`, `build-report.json`입니다. vendor·vbmeta는 라이선스 고지를 보존한 텍스트와 파일시스템 재구성에 따라 기존 배포 이미지와 해시가 달라질 수 있습니다.

Ubuntu 22.04.5 aarch64 VM의 임시 디렉터리에서 기존 릴리스 모듈과 새로 컴파일한 모듈로 각각 이미지 6개를 생성했습니다. `e2fsck -fn` 전후 검사, SELinux 정책 SHA-256, 각 파일의 내용·SELinux 라벨 읽기 확인, AVB 키·서명·해시 트리 검증을 통과했습니다. 기존 모듈을 사용한 빌드에서 `boot_a`, `init_boot_a`, `dtbo_a`, `vendor_boot_a`가 2026-11-24 배포와 바이트 단위로 일치했습니다. 두 빌드에서 새로 생성한 vendor·vbmeta와 새 모듈을 사용한 vendor boot는 그 빌드의 보고서에 기록된 해시로 검증했습니다. 새 이미지의 보드 쓰기와 부팅은 미검증입니다.

## 기존 eMMC boot0 재구성

```sh
./scripts/build.sh boot0 --base "$ORIGINAL_BOOT0_BACKUP" \
  --binaries "$REFERENCE_UBOOT_DIR" --output "$CRZ_BOOT0_OUT"
```

해시가 고정된 기존 4 MiB boot0 백업과 릴리스 부트로더 파일 3개를 사용합니다. 512바이트 쓰기 단위의 끝을 0으로 맞추고 그 밖의 바이트는 백업에서 보존합니다. 이렇게 재조합한 파일이 당시 보드 읽기 해시와 바이트 단위로 일치하는 것을 확인했습니다. `boot0.img`나 보드 백업은 별도로 관리합니다.
