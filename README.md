# CRZ AM62x Android 포팅

CRZ AM625 GP 보드에서 TI Processor SDK Android **11.00.01**의 Android 16 eMMC 배포본을 사용하기 위한 포팅 변경 모음입니다. 재현 기준은 TI 사전 빌드 이미지와 U-Boot·커널 소스의 고정 revision입니다. 실제 개발에서는 기존 Android 이미지에 부트로더, LCD·터치 설정, 커널 모듈, vendor 설정을 반영했습니다.

| 항목 | 기준 |
| --- | --- |
| 보드 | CRZ AM625 GP, RAM 1 GiB, BSD101WX1-300 1280×800 LCD |
| 개발 호스트 | Ubuntu 22.04.5 LTS aarch64, UTM |
| Android | TI AM62x Android 16 SDK 11.00.01, eMMC userdebug 배포본 |
| 실행 커널 | `6.12.23-android16-5-gaf4cb0e2168b-4k` |
| U-Boot | 2025.01, TI `ef2eb76b650415637bd93b0eddfb1e31489117f9` 기반 |

## 변경 사항

CRZ용 U-Boot A53/R5 설정과 Android 부팅 처리, LCD·터치 DTB, 백라이트 권한·SELinux, USB 오디오 정책과 512 MiB zram을 반영했습니다. 배포 커널은 TI의 순정 `boot.img`를 사용하며, LCD·터치·zram 모듈은 `vendor_boot` ramdisk에서 로드합니다. [파일별 변경 목록](docs/change-inventory.md)

## 저장소 구조

| 경로 | 내용 |
| --- | --- |
| `manifest/` | TI 릴리스, 소스 SHA, 이미지·모듈·정책 해시 |
| `patches/` | U-Boot, 패널, vendor boot 구성 및 vendor 파일 패치 |
| `overlay/` | 신규 VINTF 선언과 LCD·터치 설계용 DTS overlay |
| `apply_change.sh` | 기준 확인, 사전 검사, 작업 사본에 패치 적용 |
| `scripts/` | 빌드, SD/eMMC 대상 확인과 쓰기, 이미지·UART·ADB 검사 |
| `docs/` | 환경, 준비, 빌드, 설치·검증 및 [포팅 참고 사항](docs/porting-notes.md) |

## 준비와 적용

[개발 환경](docs/environment.md)과 [재현 입력](docs/reproduction-inputs.md)에 따라 TI `AM62x_userdebug_11.00.01_emmc.tar`를 별도 디렉터리에 풉니다. `TI_IMAGES`는 압축 해제 후 `boot.img`와 `super.img`가 있는 디렉터리입니다.

```sh
./apply_change.sh --check --images-only "$TI_IMAGES"
./apply_change.sh --images-only --work-dir "$CRZ_WORK" "$TI_IMAGES"
```

U-Boot 및 패널 소스까지 적용하려면 `--images-only` 대신 소스 옵션을 지정합니다. 기준 SHA와 출력 경로는 [빌드 안내](docs/build-guide.md)에 있습니다.

## 빌드·설치·검증

1. [빌드 안내](docs/build-guide.md)에 따라 U-Boot와 모듈 또는 Android 이미지 묶음을 준비합니다.
2. [SD·eMMC 설치 안내](docs/flashing-guide.md)에서 보드와 대상을 먼저 확인합니다. `flash.sh`는 기본값으로 사전 검사만 수행합니다.
3. UART에서 U-Boot와 Android 초기 로그를 확인하고, 연결된 ADB 장치에서 Android 버전, 부팅 완료, FBE, SELinux 및 zram을 확인합니다. [보드 검증 항목](docs/flashing-guide.md#부팅과-주변장치-검증)

기존 보드 기록에서 SD 없는 eMMC 냉간 부팅, LCD·터치·스크롤, 암호화 유지, SELinux Enforcing, 512 MiB zram 및 오디오 정책 초기화를 확인했습니다. 빈 eMMC 전체 설치, USB 마이크 녹음, deep suspend는 미검증입니다. 재부팅 후 홈 아이콘이 간헐적으로 비는 문제와 터치 IRQ 제약은 [문제 해결](docs/troubleshooting.md)에 정리했습니다.

Ubuntu VM에서 순정 이미지와 기존 검증 모듈을 사용해 슬롯 A 이미지 6개를 재생성했습니다. ext4와 AVB 검증을 통과했으며 `vendor_boot_a`는 기존 배포본과 바이트 단위로 일치했습니다. 이 재생성 묶음의 보드 설치와 부팅은 미검증입니다.

[재현성 검증 결과](docs/verification.md)에는 독립 빌드의 해시, U-Boot 교차 빌드, 현재 보드의 UART 읽기와 저장소 점검을 기록했습니다.

## 참고 자료

- [TI Android 11.00.01 릴리스 노트](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/devices/AM62X/android/Release_Specific_Release_Notes.html)
- [TI 릴리스 manifest 커밋](https://git.ti.com/cgit/android/manifest/commit/?id=dbb247c21d9142002145c2e4a109ab078e2d9590)
- [CRZ AM62x Linux 포팅 저장소](https://github.com/yoonchulroh/CRZ_AM62x_Linux)
