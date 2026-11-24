# 문제 해결

| 증상 | 확인할 내용 |
| --- | --- |
| SHA-256 또는 manifest가 다름 | TI AM62x GP eMMC **11.00.01 userdebug** 자료와 정확한 소스 기준을 확인합니다. [입력과 경로](reproduction-inputs.md) |
| 첫 DTB 패치가 실패함 | `dtc --version`이 1.7.2인지 확인합니다. 순정 `vendor_boot.img`의 SHA 및 0번 DTB 해시가 맞아야 합니다. |
| 적용 디렉터리가 이미 있음 | 스크립트는 이전 결과를 검증합니다. 다른 버전이나 수정한 작업은 보존하고 새 출력 경로로 다시 준비하세요. 비정상 종료 뒤 생긴 잠금 디렉터리는 활성 프로세스가 없는지 확인한 뒤 처리합니다. |
| 모듈 해시가 다름 | 정확한 `.config`, `Module.symvers`, 헤더와 Clang r536225를 확인합니다. 새 패널·PWM 모듈은 `--module-symvers`를 지정해 ABI를 검증합니다. TI 제공 모듈 3개는 기준 해시가 일치해야 합니다. |
| vendor 이미지 또는 AVB가 실패함 | `secilc` 출력, 정책 입력 해시, `fec` 실행 환경, 순정 `vbmeta`가 신뢰하는 공개 키를 확인합니다. 빌드 로그와 입력을 보존하세요. |
| SD로만 부팅됨 | SW1, SD 분리, UART의 두 SPL, eMMC boot0 및 EXT_CSD를 확인합니다. eMMC 사용자 영역과 boot0를 구분합니다. |
| `enablefilecrypto_failed` | 기존 보드에서 복호화된 F2FS의 encrypt 기능 플래그 누락이 원인이었습니다. raw 암호화 userdata에 평문 파일시스템 복구 명령을 실행하면 손상이 발생할 수 있습니다. UART와 백업을 먼저 확보합니다. |
| 홈 아이콘이 비어 있음 | 기존 시험에서 설정 화면을 열고 홈으로 복귀하면 표시가 돌아왔습니다. 간헐 재현이 남아 있고 영구 수정은 미확인입니다. |
| zram 크기 확인에서 권한 거부 | SELinux Enforcing 상태에서는 일반 셸이 zram sysfs를 읽지 못할 수 있습니다. CRZ userdebug에서는 UART의 `su 0 cat /sys/block/zram0/disksize`를 사용하거나 ADB 검증에 `--with-su`를 추가합니다. |
| 터치 또는 깨우기 문제 | 현재 동작 검증은 17 ms 폴링입니다. GPIO IRQ 경로와 깊은 절전·터치 깨우기는 미검증입니다. |
| 오디오 재생·녹음이 안 됨 | 무음 stub과 오디오 정책 초기화 여부, USB 장치 열거, 실제 USB 마이크 녹음을 각각 확인합니다. 아날로그 WM8960은 미해결입니다. |

플래싱 중 오류가 나면 부팅을 계속하기 전에 쓰기 응답, 적용된 파티션 및 백업을 확인합니다. `vendor_boot_a`, `vendor_a`, `vbmeta_a`는 같은 묶음으로 유지합니다. 부트로더·커널·파티션의 확인된 조합은 [manifest](../manifest/ti-11.00.01.json)에 있습니다.
