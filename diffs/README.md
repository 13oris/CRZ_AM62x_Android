# 파일별 diff

로컬 생성본에서 `diffs/<상대 경로>.diff`는 `original_files/<상대 경로>`를 `changed_files/<상대 경로>`로 바꿉니다. 수정 19건을 각각 생성하며, 생성 도구가 전체 diff를 원본 사본에 적용해 결과의 해시를 확인합니다.

실제 SDK 적용은 [`patches/`](../patches/)와 [`overlay/`](../overlay/)를 사용합니다. [생성 안내](../docs/review-files.md) · [파일 목록과 SHA-256](../manifest/review-files.json)
