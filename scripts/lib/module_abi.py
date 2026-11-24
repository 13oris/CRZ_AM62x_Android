"""Validate the two rebuilt external modules against the recorded GKI ABI."""

from .common import MANIFEST, expect_hash, require
from .image_formats import le


REBUILT_MODULES = {"panel-simple.ko": "panel_simple", "pwm_bl.ko": "pwm_bl"}


def kernel_exports(path):
    expect_hash(path, MANIFEST["module_build_abi"]["module_symvers_sha256"])
    symbols = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            crc, name, *_ = line.split()
            symbols[name] = int(crc, 16)
    return symbols


def sections(blob):
    require(blob[:6] == b"\x7fELF\x02\x01" and le("HH", blob, 16) == (1, 183),
            "AArch64 relocatable ELF 커널 모듈이 필요합니다.")
    at, = le("Q", blob, 40)
    width, count, names_at = le("HHH", blob, 58)
    require(width == 64 and names_at < count and at + width * count <= len(blob), "ELF 섹션 헤더 범위 오류")
    headers = [le("IIQQQQIIQQ", blob, at + n * width) for n in range(count)]
    name_header = headers[names_at]
    names = blob[name_header[4]:name_header[4] + name_header[5]]
    result = {}
    for index, typ, _, _, offset, length, *_ in headers:
        require(index < len(names), "ELF 섹션 이름 범위 오류")
        name = names[index:].split(b"\0", 1)[0].decode("ascii")
        if typ != 8:  # SHT_NOBITS has no on-disk payload.
            require(offset + length <= len(blob), f"ELF 섹션 범위 오류: {name}")
            result[name] = blob[offset:offset+length]
    return result


def verify_module_abi(blob, filename, exports):
    data = sections(blob)
    basic = data.get("__versions", b"")
    require(len(basic) % 64 == 0, "모듈 symbol version 레코드 크기 불일치")
    imports = {}

    def record(raw, crc):
        symbol = raw.split(b"\0", 1)[0].decode("ascii")
        require(symbol and (symbol not in imports or imports[symbol] == crc),
                f"모듈 symbol version 중복 또는 오류: {symbol}")
        imports[symbol] = crc

    for i in range(0, len(basic), 64):
        record(basic[i+8:i+64], le("Q", basic, i)[0])
    if "__version_ext_crcs" in data:
        names = data["__version_ext_names"].rstrip(b"\0").split(b"\0")
        crcs = data["__version_ext_crcs"]
        require(len(crcs) == len(names) * 4, "확장 symbol version 크기 불일치")
        for i, name in enumerate(names):
            record(name, le("I", crcs, i * 4)[0])
    require("module_layout" in imports, "모듈 레이아웃 CRC가 없습니다.")
    mismatches = sorted(name for name, crc in imports.items() if exports.get(name) != crc)
    require(not mismatches, f"{filename} ABI CRC 불일치: {', '.join(mismatches)}")
    require(not any(k.startswith(("___ksymtab", "__ksymtab")) for k in data), f"{filename}에 예상 밖 symbol export가 있습니다.")
    info = {item.decode("utf-8") for item in data[".modinfo"].split(b"\0") if item}
    version = MANIFEST["reference_release"]["running_kernel"]
    require(f"vermagic={version} SMP preempt mod_unload modversions aarch64" in info
            and f"name={REBUILT_MODULES[filename]}" in info and "depends=" in info,
            f"{filename} 모듈명, 종속성 또는 vermagic 불일치")
    if filename == "panel-simple.ko":
        require(any(x.startswith("alias=") and "bestar,bsd101wx1-300" in x for x in info),
                "BSD101WX1-300 패널 모듈 alias가 없습니다.")
    return len(imports)
