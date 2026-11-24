# 검토용 사본의 라이선스와 변경 고지

`original_files/`는 TI 기준에서 가져온 파일이며, `changed_files/`는 CRZ AM62x Android 포팅의 수정본과 신규 파일입니다. [파일별 보기](../docs/review-files.md)의 변경 후 열과 [경로별 기록](../manifest/review-publication.json)에 변경된 파일을 모두 표시했습니다. 검토 사본은 빌드·적용 결과와 직접 비교할 수 있도록 기존 파일 안의 저작권이나 라이선스 고지를 보존하고, CRZ의 변경 고지는 아래에 함께 제공합니다.

| 검토 경로 | 배포 조건과 변경 고지 |
| --- | --- |
| `u-boot/` | TI U-Boot 2025.01의 GPL 기본 조건과 파일별 SPDX·저작권이 적용됩니다. CRZ 변경은 2026-11-24 포팅 기록 기준이며, A53/R5 구성, CRZ 보드 DTS, Android 이미지 로딩 및 ramdisk·bootconfig 처리가 포함됩니다. [GPL v2 전문](GPL-2.0.txt) · [TI U-Boot 라이선스 안내](https://github.com/TexasInstruments/ti-u-boot/blob/ef2eb76b650415637bd93b0eddfb1e31489117f9/Licenses/README) |
| `kernel/drivers/gpu/drm/panel/panel-simple.c` | 양쪽 파일의 NVIDIA 2013 허용 고지를 유지했습니다. CRZ 변경은 BSD101WX1-300 패널 타이밍과 패널 식별자 추가입니다. |
| `kernel/crz-bsd101wx1-300.dtso` 및 `u-boot/dts/upstream/src/arm64/ti/k3-am625-crz.dts` | 파일 헤더의 GPL-2.0-only 또는 MIT 선택 조건을 유지했습니다. 전자는 설계 참고이며, 후자는 CRZ의 A53 보드 DTS입니다. [GPL v2 전문](GPL-2.0.txt) · [MIT 전문](MIT.txt) |
| `vendor-boot-header/cmdline.txt` | TI 2022 Apache-2.0 보드 설정에서 이어지는 헤더 인자입니다. CRZ가 CMA 크기와 UART 진단 관련 인자를 수정했습니다. [Apache 2.0 전문](Apache-2.0.txt) |
| `vendor/etc/fstab.am62.mmc`, `vendor/etc/fstab.am62.mmc.avb` | Texas Instruments의 2023 빌드 규칙이 속한 Soong 패키지의 기본 조건은 Android-Apache-2.0입니다. CRZ가 두 파일의 zram 크기를 수정했습니다. [Apache 2.0 전문](Apache-2.0.txt) |
| `vendor/etc/audio_policy_configuration.xml`, `vendor/etc/usb_audio_policy_configuration.xml` | 양쪽 파일의 Android Open Source Project 2015 Apache 2.0 고지를 유지했습니다. CRZ가 주 출력과 USB 입력 프로파일을 변경했습니다. [Apache 2.0 전문](Apache-2.0.txt) |
| `vendor/etc/vintf/manifest/crz-audio-stub.xml` | CRZ가 추가한 파일입니다. 이 저장소에서 이미 추적하던 overlay와 동일하며 별도 공개 라이선스 지정이 없습니다. |
