# SD·eMMC 설치와 검증

## 대상 확인

CRZ AM625 GP 보드에서 SW1의 1–2–3–4 순서는 SD 부팅이 **ON–ON–ON–OFF**, eMMC 부팅이 **OFF–ON–ON–OFF**입니다. 전원을 끈 상태에서 스위치를 바꿉니다. UART를 115200 8N1로 열고 U-Boot의 보드 모델·SoC·DRAM과 MMC 목록을 확인합니다. 보드에서 eMMC는 U-Boot MMC 0, SD는 MMC 1로 확인됐습니다.

```sh
picocom -b 115200 "$UART_DEVICE"
lsblk -o NAME,SIZE,MODEL,TRAN,RM,FSTYPE,MOUNTPOINTS
```

모든 `flash.sh` 명령의 기본 동작은 입력과 대상 확인입니다. 쓰기에는 `--write`와 확인 단계에서 출력한 정확한 `--confirm` 문자열이 필요합니다. 이미지 검증에는 과거 릴리스 해시 또는 같은 `build.sh images` 실행의 보고서를 사용합니다.

## SD 부트로더

기존 FAT 파티션을 Linux에 읽기·쓰기로 마운트하고, 검증된 부트로더 파일 3개가 있는 디렉터리를 지정합니다.

```sh
./scripts/flash.sh sd --binaries "$REFERENCE_UBOOT_DIR" --mount "$SD_FAT_MOUNT"
```

출력된 `SD:/dev/…`가 해당 카드 파티션인지 확인합니다. 같은 명령에 `--write --confirm "$SD_CONFIRM"`을 추가하면 FAT 루트에 `tiboot3.bin`, `tispl.bin`, `u-boot.img`를 복사하고 해시를 검사합니다. FAT 파티션이 비어 있다면 TI의 SD 부팅 준비 절차에서 파티션을 준비합니다. 장치 목록을 먼저 대조하세요. 이 FAT 구성은 U-Boot 부팅용이며, eMMC 복구 작업에는 별도로 준비한 CRZ용 SD 복구 Linux가 필요합니다. [TI 11.00.01 SD 부팅 준비](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/android/Application_Notes_Android_Bootloader_SD_Card.html)

## 빈 eMMC의 TI 기반 설치

기존 보드에서는 SD 복구 Linux에서 필요한 eMMC 영역을 교체하고 SD 없이 냉간 부팅을 확인했습니다. 빈 CRZ 보드에서 아래 TI 기반 설치를 처음부터 끝까지 시험한 결과는 **미검증**입니다.

TI 11.00.01 eMMC 전용 배포본을 준비하고 SD U-Boot에서 `mmc list`와 `fastboot 0`을 실행합니다. 호스트에서 `fastboot devices`로 대상 장치의 serial을 확인합니다. TI의 GP EVM 안내는 배포본 디렉터리에서 `sudo ./flashall.sh --board am62x-sk`로 GPT와 기반 이미지를 설치합니다. 이 명령은 eMMC 데이터를 덮어쓰기 때문에 장치가 한 대인지, 지정한 보드인지, 백업이 준비됐는지 확인하고 설치 승인 후 실행합니다. CRZ U-Boot의 RAM 환경에서는 `saveenv`를 사용하지 않습니다. [TI 11.00.01 eMMC 플래싱](https://software-dl.ti.com/processor-sdk-android/esd/AM62X/11_00_01/docs/android/Overview_Flashing.html)

## 이미 TI 기반 이미지가 있는 보드

TI 기반의 `boot_a`, `init_boot_a`, `dtbo_a`는 확인된 배포에 그대로 사용됐습니다. 적용 전 현재 시스템이 같은 TI 배포본인지 확인하고 필요한 파티션을 백업합니다. `vendor_boot_a`, 논리 `vendor_a`, `vbmeta_a`는 같은 묶음에서 준비합니다. `vbmeta_a`는 마지막에 반영하세요.

```sh
./scripts/verify.sh images --images "$CRZ_IMAGES_OUT"
./scripts/flash.sh fastboot --serial "$BOARD_SERIAL" \
  --images "$CRZ_IMAGES_OUT" --partition vendor_boot_a
```

사전 검사에서 serial, 활성 슬롯 A, 이미지 크기를 확인한 뒤 `--write --confirm "$FASTBOOT_CONFIRM"`을 추가합니다. 파티션마다 다른 확인 문자열이 출력됩니다. `vendor_a`는 fastbootd에서 `is-userspace=yes`와 `is-logical:vendor_a=yes`가 확인될 때만 이 스크립트로 적용할 수 있습니다. 새 스크립트의 fastboot 쓰기는 실기 **미검증**입니다.

이전 배포에서 사용한 방법은 SD 복구 Linux에서 **미마운트·미사용 eMMC**를 확인하고, 실제 super의 LP 메타데이터를 읽어 `vendor_a` extent만 쓰고 전체 읽기 해시를 검증하는 방식입니다. fastbootd가 작동하지 않으면 해당 복구 절차와 보드별 백업을 사용하세요. 과거 기록의 절대 오프셋을 다른 eMMC 배치에 적용하면 데이터가 손상됩니다. `vendor_a.img`는 super 전체 이미지로 사용할 수 없습니다.

## eMMC boot0

SD 복구 Linux를 실행 중인 CRZ 보드에서 4 MiB `/dev/mmcblkNboot0`을 식별합니다. 초기 보드 기록의 EXT_CSD는 `PARTITION_CONFIG=0x48`, `BOOT_BUS_CONDITIONS=0x02`였습니다. 상태가 다르면 보드 제조사 절차를 먼저 확인합니다.

```sh
./scripts/flash.sh boot0 --device "$EMMC_BOOT0" \
  --image "$CRZ_BOOT0_OUT/boot0.img" --backup "$NEW_BOOT0_BACKUP"
```

확인 결과가 맞다면 SD 복구 Linux에서 관리자 권한으로 같은 인자에 `--write --confirm "$BOOT0_CONFIRM"`을 추가합니다. 스크립트는 쓰기 보호, SD 루트, eMMC 미마운트·holder 없음, 크기와 해시를 검사합니다. 기존 4 MiB를 새 파일에 백업하고 읽기 확인을 거친 뒤 쓰며, 전체 읽기 확인 후 `force_ro=1`을 복구합니다. 스크립트로 실제 쓰는 시험은 미검증입니다. 기존 배포에서는 같은 영역에 전체 쓰기·읽기 검증과 SD 없는 냉간 부팅을 확인했습니다.

## 부팅과 주변장치 검증

1. SD를 분리한 뒤 SW1을 eMMC로 놓고 전원을 켭니다. UART에서 CRZ 보드와 GP SoC, 1 GiB, U-Boot 2025.01, Android 커널 및 정상 부팅 로그를 확인합니다.
2. 저장된 UART 로그는 `./scripts/verify.sh uart --log "$UART_LOG"`로 검사할 수 있습니다. ADB 연결 후 `adb devices -l`로 serial을 확인하고 `./scripts/verify.sh adb --serial "$ADB_SERIAL"`을 실행합니다.
3. 기존 배포에서 `sys.boot_completed=1`, 슬롯 `_a`, Android 16, FBE, `getenforce`의 `Enforcing`, zram `536870912` 바이트를 확인했습니다.
4. LCD 표시, 터치·스크롤, 3버튼 내비게이션, USB 수신기 열거, Ethernet 링크와 ping을 확인합니다. USB 마이크 실제 녹음과 장기 동작은 별도 시험이 필요합니다. 오디오 정책 초기화와 실제 녹음은 각각 확인합니다.
