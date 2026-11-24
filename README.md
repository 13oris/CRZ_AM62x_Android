# CRZ AM62x Android 포팅

CRZ AM625 GP 보드에서 TI Processor SDK Android **11.00.01**의 Android 16 eMMC 배포본을 사용하기 위한 포팅 변경 모음입니다. 재현 기준은 TI 사전 빌드 이미지와 U-Boot·커널 소스의 고정 revision입니다. 실제 개발에서는 기존 Android 이미지에 부트로더, LCD·터치 설정, 커널 모듈, vendor 설정을 반영했습니다.

| 항목 | 기준 |
| --- | --- |
| 보드 | CRZ AM625 GP, RAM 1 GiB, BSD101WX1-300 1280×800 LCD |
| 개발 호스트 | Ubuntu 22.04.5 LTS aarch64, UTM |
| Android | TI AM62x Android 16 SDK 11.00.01, eMMC userdebug 배포본 |
| 실행 커널 | `6.12.23-android16-5-gaf4cb0e2168b-4k` |
| U-Boot | 2025.01, TI `ef2eb76b650415637bd93b0eddfb1e31489117f9` 기반 |

## 저장소 사용 순서

1. [기준 입력과 패치 적용 대상](docs/reproduction-inputs.md)에서 TI SDK 자료를 준비하고 [기준 manifest](manifest/ti-11.00.01.json)의 SHA-256과 비교합니다.
2. `patches/`에서 U-Boot와 패널 소스, 추출한 DTB의 DTS, vendor ramdisk 목록, vendor 파일시스템 설정에 해당하는 패치를 작업 복사본에 적용합니다.
3. `overlay/`에는 신규 VINTF 선언과 LCD·터치 설계의 DTS overlay 소스가 있습니다. 첫 번째 DTB를 재현할 때는 [실제 배포 DTB 기준 패치](patches/vendor-boot/0001-crz-lcd-touch-dtb.patch)를 사용합니다.
4. [배포 변경 목록과 검증 범위](docs/change-inventory.md)에서 재현 결과를 확인합니다.

Phase 2의 검증 범위는 기준 파일에 대한 패치 적용과 첫 번째 DTB 재생성입니다. 전체 적용·빌드·플래싱 스크립트와 빈 eMMC 설치 검증은 후속 단계입니다.

## 참고 자료

- [TI Android 11.00.01 릴리스 노트](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/devices/AM62X/android/Release_Specific_Release_Notes.html)
- [TI 릴리스 manifest 커밋](https://git.ti.com/cgit/android/manifest/commit/?id=dbb247c21d9142002145c2e4a109ab078e2d9590)
- [CRZ AM62x Linux 포팅 저장소](https://github.com/yoonchulroh/CRZ_AM62x_Linux)
