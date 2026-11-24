# 기준 입력과 적용 대상

## TI 입력 자료

| 자료 | 기준과 용도 |
| --- | --- |
| AM62x 11.00.01 eMMC userdebug 배포본 | `AM62x_userdebug_11.00.01_emmc.tar`. 순정 `vendor_boot.img`, `super.img`, `vbmeta.img`의 입력 해시는 [manifest](../manifest/ti-11.00.01.json)에 있습니다. |
| U-Boot 소스 | TI bootloader manifest의 `u-boot` 프로젝트 `ef2eb76`. 릴리스 패치 생성에는 같은 Git 커밋의 소스 아카이브를 사용했습니다. |
| 패널 모듈 소스·ABI | `panel-simple.c`의 비교 원본은 TI `e9a61e5`입니다. 모듈 빌드 기록은 실행 커널 `af4cb0e`에 맞춘 SDK 설정, 생성 헤더, 모듈 심벌 CRC, Clang r536225를 사용했습니다. |
| vendor 트리 | TI sparse `super.img`의 LP 메타데이터로 `vendor_a`를 찾아 추출합니다. 추출 결과 SHA-256은 초기 보드 백업과 일치했습니다. |
| DTB·ramdisk | TI `vendor_boot.img`에 포함됩니다. DTB 테이블 첫 항목과 ramdisk의 적용 방법은 아래에서 확인할 수 있습니다. |

두 커널 SHA는 서로 분기된 TI 소스입니다. 배포된 커널 페이로드는 순정 TI `boot.img`와 동일합니다. 별도 커널 개발 트리 전체를 처리하는 작업과 패널 외부 모듈 빌드는 별개입니다. [TI 커널 SHA 비교](https://github.com/TexasInstruments/ti-linux-kernel/compare/e9a61e5d367622946887c99803812cd8e07b9c74...af4cb0e2168bc4db58d23c810dc74efea3b21f2a)

## 패치 및 overlay 적용 경로

아래 경로를 각각 작업 디렉터리로 사용합니다. `git apply --check`로 사전 검사한 뒤 파일 패치를 적용할 수 있습니다. 패치에는 순정 파일의 경로를 기준으로 한 `a/`와 `b/` 접두사가 있습니다.

| 저장소 경로 | 적용 루트 또는 파일 |
| --- | --- |
| `patches/u-boot/0001-crz-am625-android-boot.patch` | TI `u-boot` 프로젝트 루트 |
| `patches/kernel/0001-panel-simple-crz-bsd101wx1-300.patch` | 패널 소스 기준 `e9a61e5`의 커널 소스 루트 또는 해당 경로를 담은 모듈 빌드 복사본 |
| `patches/vendor-boot/0001-crz-lcd-touch-dtb.patch` | 순정 DTB 테이블 0번을 DTC 1.7.2로 디컴파일해 `crz-vendor-boot-dtb0.dts`를 만든 디렉터리 |
| `patches/vendor-boot-header/0001-crz-kernel-cmdline.patch` | 순정 vendor boot 헤더의 커널 cmdline을 추출한 `cmdline.txt`의 디렉터리 |
| `patches/vendor-boot-ramdisk/0001-crz-module-lists.patch` | 순정 vendor ramdisk에서 추출한 CPIO의 루트 |
| `patches/vendor/0001-crz-backlight.patch` | 추출한 `vendor_a` 파일시스템의 루트 |
| `patches/vendor/0002-crz-audio-policy.patch` | 같은 `vendor_a` 루트 |
| `patches/vendor/0003-crz-zram512.patch` | 같은 `vendor_a` 루트 |
| `overlay/vendor/etc/vintf/manifest/crz-audio-stub.xml` | vendor 루트 `etc/vintf/manifest/crz-audio-stub.xml`에 신규 추가 |
| `overlay/kernel/crz-bsd101wx1-300.dtso` | 기준 DTS 노드와 결선을 설명하는 설계 소스 |

DTB 재생성에서는 `dtc -I dtb -O dts`로 추출 항목을 변환하고, 패치를 적용한 뒤 `dtc -I dts -O dtb`를 사용했습니다. 이 방법으로 첫 항목의 결과 SHA-256이 11월 24일 릴리스와 일치했습니다. DTB 배치를 다시 만들 때는 나머지 5개 항목과 bootconfig를 보존합니다.

ramdisk 목록과 함께 필요한 `edt-ft5x06.ko`, `zram.ko`, `zsmalloc.ko`는 일치하는 TI SDK에서 준비합니다. `panel-simple.ko`와 `pwm_bl.ko`는 대상 커널 ABI에 맞춰 빌드합니다. [manifest](../manifest/ti-11.00.01.json)의 모듈 해시는 과거 배포본을 식별합니다.

vendor 적용 시 두 오디오 XML의 AOSP 고지를 보존합니다. XML 요소와 속성은 기존 배포본과 동일하게 검증했습니다. 고지 문자열을 보존한 파일은 기존 배포본과 바이트가 다르므로 새 vendor·vbmeta의 해시는 해당 입력으로 재생성한 뒤 따로 기록해야 합니다. SELinux 정책 바이너리와 AVB 메타데이터는 소스 변경을 반영해 다시 생성해야 합니다.

## 배포 자료와 출처

현재 저장소는 이미지 재생성에 필요한 소스 변경을 담습니다. TI 원본 및 사전 빌드 바이너리는 TI 배포본에서 준비합니다. 과거 릴리스 해시와 SDK 입력 식별은 [manifest](../manifest/ti-11.00.01.json)에 기록했습니다. 오디오 XML 원본 고지와 소스의 SPDX 표기를 유지했습니다. 저장소 공개 전에는 TI 패키지와 CRZ 자료의 재배포 범위를 확인해야 합니다. [TI SDK 라이선스 안내](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/devices/AM62X/android/Release_Specific_Release_Notes.html)
