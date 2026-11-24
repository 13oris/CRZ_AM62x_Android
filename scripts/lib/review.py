import difflib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

from .common import MANIFEST, ROOT, ensure_separate, expect_hash, kit_fingerprint, new_directory, require, run, sha256, write, write_json
from .prepare import STUB, prepare


CATALOG = "review-files.json"
DESIGN = "kernel/crz-bsd101wx1-300.dtso"


def sources():
    images = MANIFEST["stock_images_sha256"]
    dtb = MANIFEST["vendor_boot_dtb"]
    boot = {"image": "vendor_boot.img", "image_sha256": images["vendor_boot.img"]}
    return {
        "u-boot": {
            "type": "git", "project": "u-boot",
            "revision": MANIFEST["project_revisions"]["bootloader"]["u-boot"],
        },
        "kernel": {
            "type": "git", "project": "ti-linux-kernel",
            "revision": MANIFEST["panel_source"]["revision"],
        },
        "vendor-boot": {
            "type": "decompiled-dtb", **boot, "dtb_entry": dtb["entry"],
            "dtb_sha256": dtb["before_sha256"], "dtc_version": dtb["dtc_version"],
        },
        "vendor-boot-header": {
            "type": "extracted-header", **boot, "field": "vendor_cmdline (LF-terminated text)",
        },
        "vendor-boot-ramdisk": {
            "type": "extracted-cpio", **boot, "entry": "vendor ramdisk",
        },
        "vendor": {
            "type": "extracted-ext4", "image": "super.img", "image_sha256": images["super.img"],
            "partition": "vendor_a", "partition_sha256": images["vendor_a"],
        },
    }


def unified_diff(path, before, after):
    name = path.as_posix().encode()
    lines = difflib.diff_bytes(difflib.unified_diff, before.splitlines(keepends=True),
                               after.splitlines(keepends=True), b"a/" + name, b"b/" + name)
    return b"".join(line if line.endswith(b"\n") else line + b"\n\\ No newline at end of file\n"
                    for line in lines)


def export_review(args):
    require((args.uboot or args.uboot_archive) and (args.kernel or args.kernel_archive),
            "전체 검토본에는 U-Boot와 커널 기준 소스를 모두 지정하세요.")
    output = args.output.resolve()
    supplied = (args.android_root, args.images, args.uboot, args.uboot_archive, args.kernel, args.kernel_archive)
    ensure_separate(output, [p.resolve() for p in supplied if p is not None])
    with new_directory(output) as stage, tempfile.TemporaryDirectory(prefix="crz-review-") as tmp:
        scratch = Path(tmp).resolve()
        original = stage / "original_files"
        changed = stage / "changed_files"
        diffs = stage / "diffs"
        entries = {}

        def record(path, before, after, application, source=None):
            name = path.as_posix()
            require(name not in entries, f"검토 파일에 적용 출처가 중복됩니다: {name}")
            require(b"\0" not in after and (before is None or b"\0" not in before),
                    f"텍스트 검토 트리에 바이너리를 포함할 수 없습니다: {name}")
            after.decode("utf-8")
            new = changed / path
            write(new, after)
            entry = {"path": name, "status": "added", "changed_sha256": sha256(new),
                     "application": application, "publication": "review-required"}
            if source:
                entry["original_source"] = source
            if before is not None:
                before.decode("utf-8")
                require(before != after, f"패치로 내용이 바뀌지 않았습니다: {name}")
                old = original / path
                diff = diffs / (name + ".diff")
                write(old, before)
                write(diff, unified_diff(path, before, after))
                entry.update(status="modified", original_sha256=sha256(old), diff_sha256=sha256(diff))
            entries[name] = entry

        def record_patch(patch_path, relative, before, after):
            group = patch_path.parent.name
            record(Path(group) / relative, before, after, patch_path.relative_to(ROOT).as_posix(),
                   group if before is not None else None)

        prepared = scratch / "prepared"
        apply_args = SimpleNamespace(**vars(args), check=False, images_only=False, work_dir=prepared)
        prepare(apply_args, record=record_patch)
        stub = Path("vendor") / STUB
        record(stub, None, (prepared / stub).read_bytes(), "overlay/" + stub.as_posix())
        record(Path(DESIGN), None, (ROOT / "overlay" / DESIGN).read_bytes(), "design-only")
        entries[DESIGN]["status"] = "reference"

        # This verifies the generated display diffs independently from the apply patches.
        verified = scratch / "diff-check"
        shutil.copytree(original, verified)
        for name, entry in sorted(entries.items()):
            if entry["status"] == "modified":
                run("git", "apply", "--whitespace=nowarn", diffs / (name + ".diff"), cwd=verified)
                expect_hash(verified / name, entry["changed_sha256"])
        modified = sum(e["status"] == "modified" for e in entries.values())
        added = sum(e["status"] == "added" for e in entries.values())
        reference = len(entries) - modified - added
        catalog = {
            "schema_version": 1,
            "sdk": MANIFEST["sdk"],
            "apply_inputs_sha256": kit_fingerprint(),
            "counts": {"original_files": modified, "changed_files": len(entries), "diffs": modified,
                       "additions": added, "design_references": reference},
            "sources": sources(),
            "files": [entries[name] for name in sorted(entries)],
        }
        pinned = ROOT / "manifest" / CATALOG
        if pinned.is_file() and not args.refresh_catalog:
            require(catalog == json.loads(pinned.read_text(encoding="utf-8")),
                    "생성한 검토 파일이 저장소 인덱스와 다릅니다. 변경을 검토할 때는 --refresh-catalog를 사용하세요.")
        write_json(stage / CATALOG, catalog)
        write(stage / "README.txt", (
            "CRZ AM62x Android 파일 검토본\n\n"
            f"original_files/ {modified}개 · changed_files/ {len(entries)}개 · diffs/ {modified}개\n"
            f"추가 파일 {added}개, 설계 참고 파일 {reference}개를 변경본에 포함했습니다.\n"
            "review-files.json에서 각 파일의 기준 출처, SHA-256 및 실제 적용 경로를 확인할 수 있습니다.\n"
            "모든 diff를 원본 사본에 적용하고 대응 변경본의 SHA-256과 일치함을 확인했습니다.\n"
            "이 검토본은 보유한 SDK에서 생성한 로컬 자료입니다. 재배포 전에 파일별 조건을 확인하세요.\n"
        ).encode("utf-8"))
    print(f"검토본 생성 완료: {output}")
