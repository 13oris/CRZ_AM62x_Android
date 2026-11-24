# CRZ AM62x Android 포팅

CRZ AM625 GP 보드에서 TI Processor SDK Android **11.00.01**의 Android 16 eMMC 배포본을 사용하기 위한 포팅 변경 모음입니다. 재현 기준은 TI 사전 빌드 이미지와 U-Boot·커널 소스의 고정 revision입니다. 실제 개발에서는 기존 Android 이미지에 부트로더, LCD·터치 설정, 커널 모듈, vendor 설정을 반영했습니다.

| 항목 | 기준 |
| --- | --- |
| 보드 | CRZ AM625 GP, RAM 1 GiB, BSD101WX1-300 1280×800 LCD |
| 개발 호스트 | Ubuntu 22.04.5 LTS aarch64, UTM |
| Android | TI AM62x Android 16 SDK 11.00.01, eMMC userdebug 배포본 |
| 실행 커널 | `6.12.23-android16-5-gaf4cb0e2168b-4k` |
| U-Boot | 2025.01, TI `ef2eb76b650415637bd93b0eddfb1e31489117f9` 기반 |

## TI에서 받은 기준 입력

| 입력 | 사용한 내용 |
| --- | --- |
| TI U-Boot 2025.01 `ef2eb76` | A53/R5 defconfig와 CRZ DTS 및 Android 부팅 코드의 기준 소스 |
| TI 커널 소스 `e9a61e5` | `panel-simple.c` 패치의 기준 소스 |
| TI `AM62x_userdebug_11.00.01_emmc.tar` | 순정 `boot.img`의 `af4cb0e` 계열 Android 커널, `init_boot.img`, `vendor_boot.img`, `super.img` 등 |

포팅은 TI 배포 이미지를 기준으로 진행했습니다. 전체 AOSP 빌드와 `lunch`는 사용하지 않았습니다. `e9a61e5`는 패널 소스 기준이고, `af4cb0e`는 `boot.img`로 이미 배포된 커널 기준입니다. 순정 커널을 유지하면서 CRZ LCD를 지원하기 위해 패널 모듈을 기존 커널의 ABI에 맞춰 별도로 빌드했습니다. [TI 입력과 해시](manifest/ti-11.00.01.json) · [재현 입력](docs/reproduction-inputs.md)

`vendor_boot.img`에서 0번 DTB를 꺼내 DTC 1.7.2로 DTS를 생성하고, 헤더의 `vendor_cmdline`을 줄바꿈을 붙인 텍스트로 추출했습니다. vendor ramdisk CPIO에서 모듈 목록을, `super.img`의 ext4 `vendor_a`에서 설정을 추출했습니다. [추출 방식과 기준 이미지 해시](manifest/review-files.json)

## 변경 사항

- **U-Boot 수정 8개, 신규 5개.** A53/R5 defconfig와 CRZ DTS로 보드 메모리와 부팅 구성을 반영했습니다. Android 헤더 v4의 `init_boot`에서 generic ramdisk를 읽고, 기존 vendor ramdisk와 bootconfig 인자·트레일러를 처리하도록 했습니다.
- **커널·vendor boot.** 패널 설정과 LCD·터치 DTB를 적용했습니다. `vendor_boot`의 헤더 인자와 ramdisk 모듈 로드·의존성 목록을 조정했습니다.
- **vendor.** 백라이트 권한과 SELinux, USB 오디오 정책, Audio HAL stub, zram 512 MiB를 반영했습니다. 현재 패치는 두 오디오 XML의 AOSP 저작권·Apache 2.0 고지를 보존합니다. 기존 보드 배포본과 XML의 요소와 속성은 일치하고, 주석을 포함한 파일 바이트 및 결과 `vendor_a`·`vbmeta_a` 해시는 다릅니다. [파일별 변경 목록](docs/change-inventory.md) · [기존 배포와 재생성 결과](docs/verification.md)

## 원본·변경본·diff 보기

[파일별 보기](docs/review-files.md)에서 같은 행의 링크로 원본 14개, 변경·추가·참고 파일 21개, 파일별 diff 14개를 직접 열 수 있습니다. 재배포 근거 확인을 보류한 5건과 순정 입력으로 전체 검토본을 생성하는 방법도 함께 기록했습니다.

## 저장소 구조

| 경로 | 내용 |
| --- | --- |
| `manifest/` | TI 릴리스, 소스 SHA, 이미지·모듈·정책 해시 |
| [`original_files/`](original_files/README.md) | TI 순정 기준 파일 전문 |
| [`changed_files/`](changed_files/README.md) | CRZ 적용 후 파일 전문, 신규 파일과 설계 참고 DTS |
| [`diffs/`](diffs/README.md) | 같은 상대 경로의 파일별 unified diff |
| [`licenses/`](licenses/README.md) | 검토용 파일의 라이선스 전문과 변경 고지 |
| `patches/` | U-Boot, 패널, vendor boot 구성 및 vendor 파일 패치 |
| `overlay/` | 신규 VINTF 선언과 LCD·터치 설계용 DTS overlay |
| `apply_change.sh` | 기준 확인, 사전 검사, 작업 사본에 패치 적용 |
| `scripts/` | 빌드, SD/eMMC 대상 확인과 쓰기, 이미지·UART·ADB 검사 |
| `docs/` | 환경, 준비, 빌드, 설치·검증 및 [포팅 참고 사항](docs/porting-notes.md) |

[파일별 검토본 생성](docs/review-files.md)에서는 고정된 TI 입력으로 원본 19개, 변경·추가·참고 파일 26개, 파일별 diff 19개를 생성합니다. [검토 파일 인덱스](manifest/review-files.json)에 파일별 SHA-256과 출처가 있습니다.

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
