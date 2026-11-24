# 2026-11-24 재현성 검증

Ubuntu 22.04.5 aarch64 VM에서 TI 11.00.01의 순정 입력과 별도의 임시 작업 디렉터리를 사용했습니다. 기존 CRZ 보드는 UART 읽기만 수행했습니다.

## 패치 및 Android 이미지

| 검증 항목 | 결과 |
| --- | --- |
| 전체 사전 검사 | 순정 TI eMMC 이미지, `ef2eb76` U-Boot 및 `e9a61e5` 패널 소스 기준으로 패치 8개 적용과 역적용 사전 검사 성공 |
| 두 독립 작업 사본 | 준비 기록과 적용 파일 해시 일치 |
| 첫 번째 vendor boot DTB | 배포 DTB와 바이트 일치 |
| LCD·PWM 모듈 | 기존 VM의 정확한 ABI로 재컴파일했습니다. `panel-simple.ko` import CRC 57개, `pwm_bl.ko` 26개가 일치했습니다. |
| Android 이미지 | 배포 모듈을 고정한 두 독립 빌드에서 출력 이미지 6개의 SHA-256이 모두 일치했습니다. ext4, SELinux 정책, AVB 검증을 통과했습니다. |
| 새 모듈을 포함한 묶음 | 빌드와 ABI·ext4·AVB 검증에 성공했습니다. 새 모듈과 새 이미지의 실기 로드는 미검증입니다. |
| 기존 eMMC boot0 | 배포된 부트로더 3개와 원래 4 MiB 백업에서 복원한 이미지가 보드 읽기 해시와 일치했습니다. |

첫 반복 빌드에서 ext4 수정 시간이 달라 `vendor_a` 및 루트 `vbmeta_a`의 해시가 바뀌었습니다. `debugfs`와 ext4 검사에 순정 superblock의 쓰기 시간 `1770742997`을 사용해 차이를 제거했습니다. 배포 모듈을 고정한 반복 시험의 결과는 아래와 같습니다. [e2fsprogs의 빌드 시간 처리](https://kernel.googlesource.com/pub/scm/fs/ext2/e2fsprogs.git/+/next/lib/ext2fs/openfs.c)

| 파일 | 두 독립 빌드의 SHA-256 |
| --- | --- |
| `boot_a.img` | `21975e492cbbca238bdeb584cc8bbfb5a17547a474483829285542ff49e5b2ff` |
| `init_boot_a.img` | `1badb8e97810ed11480a5fe8baa52fde9ab948912f04afc98051839eb9342a00` |
| `dtbo_a.img` | `a9a089f2caf60865057c45da353701f332da11222fd2cc1c78b8a68ebc326fec` |
| `vendor_boot_a.img` | `78f6e43aefb8c4bcc2397b0428e44901c771ebcb58296a8c000e3779ad877c19` |
| `vendor_a.img` | `f949806896849ed516ab89f72be1323e3fa8bb4b37c518f38c3f44e0f1a6ae17` |
| `vbmeta_a.img` | `b24c8de6caf148a0169e6da67d5aa77065f093d9ac9edb86ab17f68e16099096` |

## 부트로더

TI의 `ef2eb76` Git 커밋을 깨끗한 디렉터리에 받아 CRZ 패치를 적용했습니다. Ubuntu 네이티브 GCC 교차 도구로 GP R5 `tiboot3.bin`과 A53 `tispl.bin`, `u-boot.img`를 만들었습니다. A53은 이전 배포 FIT에서 추출한 BL31·OP-TEE 페이로드를 입력으로 사용했고, 출력 FIT가 `k3-am625-crz` 설정을 사용하는 것을 확인했습니다. 이 결과는 배포 이미지와 SHA-256이 다르고 실기 부팅은 미검증입니다.

별도 시험에서는 TI 부트로더 manifest의 Git 프로젝트 7개를 정확한 SHA로 준비한 뒤 `scripts/build.sh uboot --native-toolchains`를 실행했습니다. Ubuntu 22.04.5 aarch64의 GNU 교차 GCC 11.4.0으로 TI `build_all.sh` 경로의 TF-A, GP R5, OP-TEE, A53 빌드가 완료됐습니다. 초기 Git 아카이브 적용에서 Ubuntu Python의 상대 심볼릭 링크 검사 문제가 드러나, 일반 파일을 먼저 처리하고 아카이브 내부로 이어지는 링크만 생성하도록 고쳤습니다. [TI 전체 부트로더 빌드 진입점](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/android/Foundational_Components_Bootloaders.html)

| 전체 소스 빌드 결과 | SHA-256 |
| --- | --- |
| `tiboot3.bin` | `f3e9b7e3538f97f05554e5b525c085d74c38e2f820282c4eb249f05cfe72bb21` |
| `tispl.bin` | `5000384281c74444da7ea5a1a5f36b1a4085b004d225ff7f5552ca629a96ceb7` |
| `u-boot.img` | `8e4f564fb7ec8ff0328a1359ef4ea1bec83f0e1b270d7dbfc96000575458ced6` |

이 결과는 세 파일 모두 기존 보드 배포 SHA-256과 다릅니다. 신규 부트로더 반복 빌드의 바이트 일치, TI의 기본 x86_64 자동 다운로드 툴체인 경로, 신규 부트로더 실기 부팅은 미검증입니다.

## 보드 읽기 결과

- Android 16, `sys.boot_completed=1`, 슬롯 `_a`, `encrypted`, `Enforcing`, `6.12.23-android16-5-gaf4cb0e2168b-4k`, zram 512 MiB를 UART에서 확인했습니다. 일반 셸의 zram 읽기는 SELinux에 의해 거부됐고, userdebug `su`로 읽은 값은 `536870912`였습니다.
- eMMC boot0와 Android 파티션·논리 파티션 6개의 전체 읽기 SHA-256이 2026-11-24 배포 기록과 일치했습니다.
- Android 화면 크기 1280×800, `backlight-crz`, FT5x06 터치 입력 장치 등록, Ethernet 링크 up, 오디오 정책 서비스 등록을 읽어 확인했습니다. 물리 터치 입력과 USB 마이크 녹음은 이번 시험에서 실행하지 않았습니다.
- 보드는 기존 이미지를 계속 사용했습니다. 새 이미지의 SD·eMMC 플래싱, 새 부팅과 빈 eMMC 전체 설치는 미검증입니다. Mac의 ADB·fastboot 장치 목록에는 보드가 나타나지 않았습니다.

## 저장소 점검

- Git 객체 무결성과 스크립트 문법을 검사했습니다. 추적 파일은 패치·설정·스크립트·문서 텍스트입니다. 빌드 이미지, 펌웨어, 커널 모듈, SDK 원본 트리 및 키 파일은 추적하지 않습니다.
- 추적 파일에서 PEM 개인 키 표기, 일반 토큰 형식, URL 내 인증정보, 개인 작업 경로를 검색했습니다. 일치 항목은 발견되지 않았습니다.
- U-Boot DTS 추가분의 TI 저작권·SPDX와 오디오 XML의 AOSP Apache 2.0 고지를 보존했습니다. 공개 전에 CRZ 팀 자료 및 패치의 재배포 권한을 확인해야 합니다. [TI SDK 라이선스 안내](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/devices/AM62X/android/Release_Specific_Release_Notes.html) · [AOSP 라이선스 고지](https://source.android.com/docs/setup/contribute/licenses)

## Git에 포함한 검토본

- 윤철님의 Linux 저장소 `fdf1195`에서 원본 41개, 변경본 83개, 파일별 diff 33개를 확인했습니다. 적용 스크립트는 별도의 패치와 overlay를 사용합니다. Android도 같은 경로로 검토 파일을 제공하고 기존 적용 절차를 유지합니다. [Linux 기준 커밋](https://github.com/yoonchulroh/CRZ_AM62x_Linux/tree/fdf119554cb6485c70a18982274c2a107b8566a4)
- 순정 TI 이미지와 고정 소스 아카이브에서 원본 19개, 변경·추가·참고 26개, diff 19개를 다시 만들었습니다. 저장소 인덱스 및 앞서 만든 로컬 검토본과 일치했습니다. TI 설정에서 재구성한 순정 헤더의 cmdline과 두 fstab도 배포 이미지 추출 텍스트와 바이트가 일치했습니다.
- Git에 넣은 원본 14개, 변경·추가·참고 21개, diff 14개의 바이트와 SHA-256을 Git 객체에서도 확인했습니다. diff 14개를 각각 원본 사본에 적용한 결과가 대응 변경본과 일치했습니다. [검토 경로와 보류 5건](review-files.md)
