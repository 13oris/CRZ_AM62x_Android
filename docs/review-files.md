# 원본·변경본·파일별 diff

Linux 팀 저장소와 같은 폴더 이름으로 파일 내용을 검토합니다. Android는 적용 경로를 U-Boot·커널 Git 프로젝트와 vendor 이미지 내부의 위치로 구분합니다. [Linux original_files](https://github.com/yoonchulroh/CRZ_AM62x_Linux/tree/fdf119554cb6485c70a18982274c2a107b8566a4/original_files)

## Git에서 직접 보기

Git에는 원본 14개, 변경·추가·참고 21개, 파일별 diff 14개가 있습니다. 같은 행의 링크에서 파일 전문과 diff를 열 수 있습니다. 목록의 변경본은 CRZ 포팅 작업이 수정하거나 추가한 파일이며, 설계 참고 DTS의 용도는 별도로 표시했습니다.

| 상대 경로 | 변경 전 | 변경 후 | 비교 | 라이선스 근거 |
| --- | --- | --- | --- | --- |
| `kernel/crz-bsd101wx1-300.dtso` | — | [변경본](../changed_files/kernel/crz-bsd101wx1-300.dtso) | 설계 참고 | GPL-2.0-only OR MIT |
| `kernel/drivers/gpu/drm/panel/panel-simple.c` | [원본](../original_files/kernel/drivers/gpu/drm/panel/panel-simple.c) | [변경본](../changed_files/kernel/drivers/gpu/drm/panel/panel-simple.c) | [diff](../diffs/kernel/drivers/gpu/drm/panel/panel-simple.c.diff) | MIT-style |
| `u-boot/arch/arm/dts/Makefile` | [원본](../original_files/u-boot/arch/arm/dts/Makefile) | [변경본](../changed_files/u-boot/arch/arm/dts/Makefile) | [diff](../diffs/u-boot/arch/arm/dts/Makefile.diff) | GPL-2.0+ [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/arch/arm/dts/k3-am62-crz-common-u-boot.dtsi` | — | [변경본](../changed_files/u-boot/arch/arm/dts/k3-am62-crz-common-u-boot.dtsi) | 신규 | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/arch/arm/dts/k3-am625-crz-binman.dtsi` | — | [변경본](../changed_files/u-boot/arch/arm/dts/k3-am625-crz-binman.dtsi) | 신규 | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/arch/arm/dts/k3-am625-crz-u-boot.dtsi` | — | [변경본](../changed_files/u-boot/arch/arm/dts/k3-am625-crz-u-boot.dtsi) | 신규 | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/arch/arm/dts/k3-am625-r5-crz.dts` | — | [변경본](../changed_files/u-boot/arch/arm/dts/k3-am625-r5-crz.dts) | 신규 | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/boot/bootmeth_android.c` | [원본](../original_files/u-boot/boot/bootmeth_android.c) | [변경본](../changed_files/u-boot/boot/bootmeth_android.c) | [diff](../diffs/u-boot/boot/bootmeth_android.c.diff) | GPL-2.0+ [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/boot/image-android.c` | [원본](../original_files/u-boot/boot/image-android.c) | [변경본](../changed_files/u-boot/boot/image-android.c) | [diff](../diffs/u-boot/boot/image-android.c.diff) | GPL-2.0+ [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/cmd/abootimg.c` | [원본](../original_files/u-boot/cmd/abootimg.c) | [변경본](../changed_files/u-boot/cmd/abootimg.c) | [diff](../diffs/u-boot/cmd/abootimg.c.diff) | GPL-2.0+ [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/configs/am62x_evm_a53_defconfig` | [원본](../original_files/u-boot/configs/am62x_evm_a53_defconfig) | [변경본](../changed_files/u-boot/configs/am62x_evm_a53_defconfig) | [diff](../diffs/u-boot/configs/am62x_evm_a53_defconfig.diff) | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/configs/am62x_evm_r5_defconfig` | [원본](../original_files/u-boot/configs/am62x_evm_r5_defconfig) | [변경본](../changed_files/u-boot/configs/am62x_evm_r5_defconfig) | [diff](../diffs/u-boot/configs/am62x_evm_r5_defconfig.diff) | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/dts/upstream/src/arm64/ti/k3-am625-crz.dts` | — | [변경본](../changed_files/u-boot/dts/upstream/src/arm64/ti/k3-am625-crz.dts) | 신규 | GPL-2.0-only OR MIT [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/include/env/ti/android.env` | [원본](../original_files/u-boot/include/env/ti/android.env) | [변경본](../changed_files/u-boot/include/env/ti/android.env) | [diff](../diffs/u-boot/include/env/ti/android.env.diff) | GPL-2.0 [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `u-boot/include/image.h` | [원본](../original_files/u-boot/include/image.h) | [변경본](../changed_files/u-boot/include/image.h) | [diff](../diffs/u-boot/include/image.h.diff) | GPL-2.0+ [근거 1](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `vendor-boot-header/cmdline.txt` | [원본](../original_files/vendor-boot-header/cmdline.txt) | [변경본](../changed_files/vendor-boot-header/cmdline.txt) | [diff](../diffs/vendor-boot-header/cmdline.txt.diff) | Apache-2.0 [근거 1](https://git.ti.com/cgit/android/device-ti-am62x/tree/am62x/BoardConfig.mk?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) [근거 2](https://git.ti.com/cgit/android/device-ti-am62x/tree/BoardConfig-common.mk?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) [근거 3](https://android.googlesource.com/platform/build/+/refs/tags/android-16.0.0_r2/core/Makefile) [근거 4](https://docs.kernel.org/admin-guide/bootconfig.html) |
| `vendor/etc/audio_policy_configuration.xml` | [원본](../original_files/vendor/etc/audio_policy_configuration.xml) | [변경본](../changed_files/vendor/etc/audio_policy_configuration.xml) | [diff](../diffs/vendor/etc/audio_policy_configuration.xml.diff) | Apache-2.0 |
| `vendor/etc/fstab.am62.mmc` | [원본](../original_files/vendor/etc/fstab.am62.mmc) | [변경본](../changed_files/vendor/etc/fstab.am62.mmc) | [diff](../diffs/vendor/etc/fstab.am62.mmc.diff) | Apache-2.0 [근거 1](https://git.ti.com/cgit/android/device-ti-am62x/tree/config/fstab/Android.bp?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) [근거 2](https://git.ti.com/cgit/android/device-ti-am62x/tree/config/fstab/fstab.in?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) |
| `vendor/etc/fstab.am62.mmc.avb` | [원본](../original_files/vendor/etc/fstab.am62.mmc.avb) | [변경본](../changed_files/vendor/etc/fstab.am62.mmc.avb) | [diff](../diffs/vendor/etc/fstab.am62.mmc.avb.diff) | Apache-2.0 [근거 1](https://git.ti.com/cgit/android/device-ti-am62x/tree/config/fstab/Android.bp?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) [근거 2](https://git.ti.com/cgit/android/device-ti-am62x/tree/config/fstab/fstab.in.avb?id=3e9c6ded05b07e6ea91df6963b0cd59f2e5b0584) |
| `vendor/etc/usb_audio_policy_configuration.xml` | [원본](../original_files/vendor/etc/usb_audio_policy_configuration.xml) | [변경본](../changed_files/vendor/etc/usb_audio_policy_configuration.xml) | [diff](../diffs/vendor/etc/usb_audio_policy_configuration.xml.diff) | Apache-2.0 |
| `vendor/etc/vintf/manifest/crz-audio-stub.xml` | — | [변경본](../changed_files/vendor/etc/vintf/manifest/crz-audio-stub.xml) | 신규 | CRZ project |

[라이선스 전문과 변경 고지](../licenses/README.md) · [파일별 재배포 검토 기록](../manifest/review-publication.json)

## 로컬 재생성 대상

다음 5건은 전문과 파일별 diff의 추가를 보류했습니다. 기존 적용용 패치에서 변경을 확인하거나 순정 SDK로 세 보기 모두를 로컬 생성할 수 있습니다.

| 상대 경로 | 보류 근거 |
| --- | --- |
| `vendor-boot-ramdisk/lib/modules/modules.dep` | 여러 모듈에서 생성한 의존성 목록입니다. 모듈별 출처와 추출 텍스트의 고지를 연결할 근거 미확인. |
| `vendor-boot-ramdisk/lib/modules/modules.load` | 이미지 빌드에서 합성한 모듈 순서입니다. 모든 입력과 산출물의 라이선스 대응 미확인. |
| `vendor-boot/crz-vendor-boot-dtb0.dts` | DTC 디컴파일로 원래 DTS/DTSI의 파일 경계와 고지가 사라졌습니다. 포함 소스와 라이선스의 대응 미확인. |
| `vendor/etc/selinux/vendor_sepolicy.cil` | 여러 소스 정책에서 생성한 CIL입니다. 생성 텍스트의 소스별 라이선스와 고지 대응 미확인. |
| `vendor/etc/ueventd.rc` | TI am62x/ueventd.am62x.rc와 바이트가 일치합니다. 해당 파일을 명시적으로 포괄하는 라이선스 또는 배포 고지 미확인. |

## 로컬 검토본 생성

[빌드 안내](build-guide.md#작업-사본-준비)의 TI 순정 이미지와 소스 아카이브를 준비합니다. `REVIEW_OUT`에는 저장소 및 SDK 밖의 새 경로를 지정합니다.

```sh
./scripts/export_review.sh \
  --uboot-archive "$TI_UBOOT_ARCHIVE" \
  --kernel-archive "$TI_KERNEL_ARCHIVE" \
  --output "$REVIEW_OUT" "$TI_IMAGES"
```

정확한 Git 체크아웃을 사용한다면 `--uboot`와 `--kernel`을 지정할 수 있습니다. AOSP 루트를 인자로 전달하는 경우 `--images "$TI_IMAGES"`를 함께 사용합니다.

생성 도구는 실제 적용 스크립트의 기준 검사와 패치 로직을 사용합니다. 각 패치의 적용 전후 텍스트를 기록한 뒤, 파일별 diff를 별도 원본 사본에 적용하고 변경본의 SHA-256과 비교합니다. 같은 경로에 기존 출력이 있으면 새 경로를 지정해야 합니다.

```text
REVIEW_OUT/
├── original_files/   19개
├── changed_files/    26개
├── diffs/            19개
├── review-files.json
└── README.txt
```

세 디렉터리의 상대 경로는 `u-boot/`, `kernel/`, `vendor-boot/`, `vendor-boot-header/`, `vendor-boot-ramdisk/`, `vendor/` 기준입니다. `changed_files/`에는 신규 6개와 설계 참고 DTS 1개가 함께 들어갑니다. 디컴파일 DTS와 헤더 추출본은 인덱스에 추출 방식을 별도로 기록합니다.

## 출처와 배포 범위

[저장소 인덱스](../manifest/review-files.json)는 파일별 변경 상태, 양쪽 SHA-256, diff SHA-256, 원본 출처와 적용 항목을 제공합니다. 일반 생성은 이 인덱스와 일치해야 합니다. 의도적으로 패치 또는 기준이 바뀌면 `--refresh-catalog`로 검토할 새 인덱스를 출력에 생성한 뒤, 확인한 인덱스만 저장소에서 갱신합니다.

전체 SDK, 순정 이미지, 펌웨어, `.ko`, 컴파일된 SELinux 정책 바이너리, AVB 키, 보드 백업은 전문 검토 트리에서 제외합니다. 이미지와 정책의 기준 해시는 [TI 입력 manifest](../manifest/ti-11.00.01.json)에 있습니다.
