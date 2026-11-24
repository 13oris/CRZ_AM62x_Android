# 원본·변경본·파일별 diff

Linux 팀 저장소와 같은 폴더 이름으로 파일 내용을 검토합니다. Android는 적용 경로를 U-Boot·커널 Git 프로젝트와 vendor 이미지 내부의 위치로 구분합니다. [Linux original_files](https://github.com/yoonchulroh/CRZ_AM62x_Linux/tree/fdf119554cb6485c70a18982274c2a107b8566a4/original_files)

## 로컬 검토본 생성

[빌드 안내](build-guide.md#작업-사본-준비)의 TI 순정 이미지와 소스 아카이브를 준비합니다. `REVIEW_OUT`에는 저장소 및 SDK 밖의 새 경로를 지정합니다.

```sh
./scripts/export_review.sh \
  --uboot-archive "$TI_UBOOT_ARCHIVE" \
  --kernel-archive "$TI_KERNEL_ARCHIVE" \
  --output "$REVIEW_OUT" "$TI_IMAGES"
```

정확한 Git 체크아웃을 사용한다면 `--uboot`와 `--kernel`을 지정할 수 있습니다. AOSP 루트를 인자로 전달하는 경우 `--images "$TI_IMAGES"`를 함께 사용합니다.

생성 도구는 실제 적용 스크립트의 기준 검사와 패치 로직을 사용합니다. 각 패치의 적용 전후 텍스트를 기록한 뒤, 파일별 diff를 별도 원본 사본에 적용하고 변경본의 SHA-256과 비교합니다. 같은 경로에 기존 출력이 있으면 새 경로를 지정해야 합니다.

```text
REVIEW_OUT/
├── original_files/   19개
├── changed_files/    26개
├── diffs/            19개
├── review-files.json
└── README.txt
```

세 디렉터리의 상대 경로는 `u-boot/`, `kernel/`, `vendor-boot/`, `vendor-boot-header/`, `vendor-boot-ramdisk/`, `vendor/` 기준입니다. `changed_files/`에는 신규 6개와 설계 참고 DTS 1개가 함께 들어갑니다. 디컴파일 DTS와 헤더 추출본은 인덱스에 추출 방식을 별도로 기록합니다.

## 출처와 배포 범위

[저장소 인덱스](../manifest/review-files.json)는 파일별 변경 상태, 양쪽 SHA-256, diff SHA-256, 원본 출처와 적용 항목을 제공합니다. 일반 생성은 이 인덱스와 일치해야 합니다. 의도적으로 패치 또는 기준이 바뀌면 `--refresh-catalog`로 검토할 새 인덱스를 출력에 생성한 뒤, 확인한 인덱스만 저장소에서 갱신합니다.

원본과 변경본 전문 및 파일별 diff는 보유한 순정 SDK에서 로컬로 생성하는 자료입니다. 저장소에는 세 폴더의 안내와 인덱스를 추적합니다. 원본 전문을 원격에 추가하려면 파일별 재배포 조건과 고지를 확인한 뒤 해당 경로를 검토합니다. 이미지·모듈·키·생성된 SELinux 정책 바이너리는 검토 트리에 포함되지 않습니다.
