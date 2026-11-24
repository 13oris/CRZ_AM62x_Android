# 파일별 unified diff

[파일별 보기](../docs/review-files.md)에서 Git에 저장한 diff 14개를 열 수 있습니다. `diffs/<상대 경로>.diff`를 원본 사본에 적용해 대응하는 변경본과 바이트가 일치하는지 확인했습니다.

실제 SDK 적용은 [apply_change.sh](../apply_change.sh)가 [patches/](../patches/)와 [overlay/](../overlay/)를 사용합니다. 순정 SDK에서 생성할 수 있는 전체 diff 19개와 보류 이유는 [검토 안내](../docs/review-files.md)에 있습니다.
