# 배포 변경 목록

기준은 TI AM62x Android 11.00.01 eMMC userdebug 배포본이며, 비교 대상은 2026-11-24 보드 읽기 해시와 일치하는 CRZ 릴리스입니다.

| 적용 위치 | 변경 |
| --- | --- |
| U-Boot `arch/arm/dts/Makefile` | 수정. CRZ R5 DTB를 빌드 목록에 등록합니다. |
| U-Boot `arch/arm/dts/k3-am62-crz-common-u-boot.dtsi`, `k3-am625-crz-binman.dtsi`, `k3-am625-crz-u-boot.dtsi`, `k3-am625-r5-crz.dts` | 추가. CRZ 공통·R5·A53 설정과 부트 이미지 구성입니다. |
| U-Boot `dts/upstream/src/arm64/ti/k3-am625-crz.dts` | 추가. CRZ A53 보드 DT입니다. |
| U-Boot `configs/am62x_evm_a53_defconfig`, `configs/am62x_evm_r5_defconfig` | 수정. CRZ DT를 선택합니다. |
| U-Boot `boot/bootmeth_android.c`, `boot/image-android.c`, `cmd/abootimg.c`, `include/image.h` | 수정. `init_boot` 주소 전달, 인자 중복 처리, ramdisk와 bootconfig 처리를 반영합니다. |
| U-Boot `include/env/ti/android.env` | 수정. 1 GiB 보드의 `vendor_boot`, `init_boot`, DT overlay 로드 주소를 설정합니다. |
| 커널 `drivers/gpu/drm/panel/panel-simple.c` | 수정. BSD101WX1-300 DPI 패널의 1280×800 타이밍을 추가합니다. |
| `vendor_boot_a` DTB 테이블 0번 | 수정. CRZ 보드 DT, LCD enable·PWM·밝기 보간, EDT 터치 17 ms 폴링을 담습니다. |
| `vendor_boot_a` ramdisk | `lib/modules/`에 `edt-ft5x06.ko`, `panel-simple.ko`, `pwm_bl.ko`, `zram.ko`, `zsmalloc.ko`를 추가합니다. `modules.load`와 `modules.dep`를 수정합니다. |
| `vendor_a`의 `etc/ueventd.rc`, `etc/selinux/vendor_sepolicy.cil`, `etc/selinux/precompiled_sepolicy` | 수정. 백라이트 권한과 sysfs 라벨을 부여합니다. `precompiled_sepolicy`는 재컴파일 산출물입니다. |
| `vendor_a`의 `etc/audio_policy_configuration.xml`, `etc/usb_audio_policy_configuration.xml` | 수정. 무음 출력 경로를 만들고 USB 입력의 고정 44.1 kHz 프로파일을 제거합니다. |
| `vendor_a`의 `etc/vintf/manifest/crz-audio-stub.xml` | 추가. Audio HAL stub을 선언합니다. |
| `vendor_a`의 `etc/fstab.am62.mmc`, `etc/fstab.am62.mmc.avb` | 수정. zram을 300 MiB에서 512 MiB로 확대합니다. |
| `vbmeta_a` | 수정. 변경된 vendor와 vendor boot의 AVB 정보를 반영합니다. |
| eMMC `boot0` | 수정. 검증된 `tiboot3.bin`, `tispl.bin`, `u-boot.img` 구성으로 재구성했습니다. |

## 검증

- U-Boot 13개 파일을 포함한 패치, 패널 패치, DTB 패치, ramdisk 목록 패치와 vendor 텍스트 패치를 각각 기준 파일에 적용했습니다. 적용 후 내용을 비교하고 역적용 사전 검사도 통과했습니다. U-Boot 패치는 원본 작업본의 공백까지 보존해 Git 적용 시 공백 경고가 나올 수 있습니다.
- DTC 1.7.2로 첫 번째 배포 DTB를 바이트 단위로 재생성했습니다. `boot_a`, `init_boot_a`, `dtbo_a`는 TI 순정 파일과 바이트가 같습니다.
- 과거 보드 읽기 결과에서 SD 없는 eMMC 부팅, 1280×800 LCD, 터치·스크롤, SELinux Enforcing, FBE, 512 MiB zram, 오디오 정책 초기화를 확인했습니다.
- 새 환경에서 U-Boot 체인과 Android 이미지 세트를 전부 재빌드하는 시험은 미검증입니다. 배포 `tispl.bin`은 당시의 보존 산출물과 일치합니다. 현재 VM의 A53 빌드 출력으로 같은 파일이 생성되는지는 미검증입니다.
- 빈 eMMC 전체 설치, USB 마이크 녹음, 터치 IRQ·deep suspend, 장기 안정성은 미검증입니다. 재부팅 뒤 홈 아이콘이 간헐적으로 비는 현상이 남아 있습니다. WM8960은 보드 시험에서 I2C 초기화에 실패했습니다.
