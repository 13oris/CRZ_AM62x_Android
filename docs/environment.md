# 개발 환경

| 항목 | 확인된 값 |
| --- | --- |
| 보드 | CRZ AM625 GP, 1 GiB RAM, eMMC, BSD101WX1-300 LCD |
| 개발 VM | UTM, Ubuntu 22.04.5 LTS, aarch64 |
| Android 기준 | TI AM62x 11.00.01 eMMC userdebug, Android 16 |
| 실행 커널 | `6.12.23-android16-5-gaf4cb0e2168b-4k` |
| U-Boot | TI 2025.01, `ef2eb76` 기반 |
| UART | 115200 baud, 8N1 |

과거 CRZ 작업에서는 전체 AOSP 빌드 및 `lunch`를 사용하지 않았습니다. TI 사전 빌드 배포본에서 시작해 필요한 부트로더, Android vendor 구성과 커널 모듈을 준비했습니다. TI 공식 AOSP·커널·부트로더 소스 위치와 프로젝트 기준 SHA는 [manifest](../manifest/ti-11.00.01.json)에 기록했습니다.

## 스크립트 의존성

| 작업 | 도구 |
| --- | --- |
| 패치 적용·사전 검사 | Python 3.10 이상, Git, LZ4, DTC 1.7.2. 전체 소스 모드는 `tarfile.data_filter`를 제공하는 업데이트된 Python 필요. |
| Android 이미지 재생성 | Linux, e2fsprogs의 `debugfs`와 `e2fsck`, AOSP `fec`, `avbtool.py`, OpenSSL, `secilc`, LZ4, 일치하는 정책 입력 및 모듈 |
| U-Boot 전체 체인 | TI 부트로더 checkout과 Linux. x86_64의 기본 경로는 TI 13.3.rel1 도구를 사용하고, `--native-toolchains`는 호스트의 `arm-linux-gnueabihf-` 및 `aarch64-linux-gnu-` 도구를 임시 빌드 사본에 연결합니다. |
| 패널 모듈 | Linux, 실제 SDK의 커널 설정·심벌·헤더, Android Clang r536225과 LLVM 도구, AArch64 GCC 도구, 호스트 컴파일러 |
| SD/eMMC 설치 | Linux의 `findmnt`, `lsblk`, `blockdev`, 또는 Android `fastboot`. UART·ADB 검증에는 UART 터미널과 `adb`가 필요합니다. |

Ubuntu 22.04의 DTC 1.6.1은 DTS 표현 차이로 이 패치에서 사전 검사에 실패합니다. 1.7.2 실행 파일이 먼저 검색되도록 별도 도구 디렉터리를 PATH에 추가하세요. DTC는 커널 도구 배포처에서 가져올 수 있습니다. [DTC 1.7.2 소스](https://www.kernel.org/pub/software/utils/dtc/) · [TI 부트로더 빌드 환경](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/android/Foundational_Components_Bootloaders.html)
