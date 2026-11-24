from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "manifest/ti-11.00.01.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
STAMP = ".crz-prepared.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(*argv, cwd=None, data=None, capture=False, quiet=False, env=None):
    return subprocess.run(
        [str(arg) for arg in argv], cwd=cwd, input=data, check=True,
        stdout=subprocess.PIPE if capture else (subprocess.DEVNULL if quiet else None), env=env,
    ).stdout


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expect_hash(path, expected):
    require(path.is_file(), f"필수 파일 없음: {path}")
    actual = sha256(path)
    require(actual == expected, f"SHA-256 불일치: {path}\n  기준 {expected}\n  실제 {actual}")


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path, data):
    write(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())


def verify_stock(images):
    for name, digest in MANIFEST["stock_images_sha256"].items():
        if name != "vendor_a":
            expect_hash(images / name, digest)


def kit_fingerprint():
    digest = hashlib.sha256()
    paths = sorted((ROOT / "patches").glob("**/[0-9][0-9][0-9][0-9]-*.patch"))
    paths.append(ROOT / "overlay/vendor/etc/vintf/manifest/crz-audio-stub.xml")
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def verify_prepared(work):
    stamp = work / STAMP
    require(stamp.is_file(), f"apply_change.sh로 준비한 작업 디렉터리가 필요합니다: {work}")
    state = json.loads(stamp.read_text(encoding="utf-8"))
    require(state["manifest_sha256"] == sha256(MANIFEST_PATH), "준비한 작업의 manifest가 다릅니다.")
    require(state.get("kit_sha256") == kit_fingerprint(), "준비한 작업의 패치 또는 overlay가 다릅니다.")
    for name, digest in state["artifacts"].items():
        rel = Path(name)
        require(not rel.is_absolute() and ".." not in rel.parts, f"잘못된 준비 기록 경로: {name}")
        path = work / rel
        require(path.resolve().is_relative_to(work), f"작업 디렉터리 밖의 기록 경로: {path}")
        expect_hash(path, digest)
    return state


def source_revision(path, revision):
    top = Path(run("git", "-C", path, "rev-parse", "--show-toplevel", capture=True).decode().strip())
    require(top.resolve() == path, f"Git 프로젝트 루트가 필요합니다: {path}")
    actual = run("git", "-C", path, "rev-parse", "HEAD", capture=True).decode().strip()
    require(actual == revision, f"Git 기준 SHA 불일치: {path}\n  기준 {revision}\n  HEAD {actual}")


def patch(root, path, record=None):
    print(f"패치 확인: {path.relative_to(ROOT)}", flush=True)
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    env["GIT_CEILING_DIRECTORIES"] = str(root.parent)
    run("git", "apply", "--check", "--whitespace=nowarn", path, cwd=root, env=env)
    lines = run("git", "apply", "--numstat", "-z", path, capture=True, cwd=root, env=env).split(b"\0")
    files = [Path(line.split(b"\t", 2)[2].decode()) for line in lines if line]
    originals = {}
    if record is not None:
        for file in files:
            require(file.parts and not file.is_absolute() and ".." not in file.parts,
                    f"검토용 패치 경로가 잘못됐습니다: {file}")
            src = root / file
            originals[file] = src.read_bytes() if src.is_file() else None
    run("git", "apply", "--whitespace=nowarn", path, cwd=root, env=env)
    run("git", "apply", "--reverse", "--check", "--whitespace=nowarn", path, cwd=root, env=env)
    if record is not None:
        for file in files:
            record(path, file, originals[file], (root / file).read_bytes())
    return [root / file for file in files]


def ensure_separate(destination, inputs):
    for source in [*inputs, ROOT]:
        if source is not None:
            require(
                not destination.is_relative_to(source) and not source.is_relative_to(destination),
                f"입력과 출력은 서로 다른 디렉터리에 있어야 합니다: {destination}, {source}",
            )


@contextmanager
def new_directory(destination):
    """Publish a private staging directory only after the caller succeeds."""
    require(destination.parent.is_dir(), f"출력 상위 디렉터리가 없습니다: {destination.parent}")
    lock = destination.with_name(destination.name + ".crz-lock")
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError(f"다른 실행이 사용 중인 출력입니다: {lock}") from exc
    try:
        require(not destination.exists() and not destination.is_symlink(), f"출력 경로가 이미 있습니다: {destination}")
        with tempfile.TemporaryDirectory(prefix=".crz-stage-", dir=destination.parent) as scratch:
            stage = Path(scratch) / "result"
            stage.mkdir(mode=0o700)
            yield stage
            require(not destination.exists() and not destination.is_symlink(),
                    f"실행 중 출력 경로가 생성됐습니다: {destination}")
            stage.rename(destination)
    finally:
        lock.rmdir()
