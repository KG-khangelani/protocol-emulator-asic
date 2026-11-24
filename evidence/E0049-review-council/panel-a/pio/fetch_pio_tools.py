# SPDX-License-Identifier: Apache-2.0
"""Extract two hash-pinned small PIO test tools into a fresh build directory."""
import argparse
import base64
from hashlib import sha256, sha512
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from urllib.request import Request, urlopen


ASSEMBLER = "https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.3.1-0/pico-sdk-tools-2.3.1-x86_64-lin.tar.gz"
EMULATOR = "https://registry.npmjs.org/rp2040js/-/rp2040js-1.4.2.tgz"


def archive(url):
    with urlopen(Request(url, headers={"User-Agent": "protocol-emulator-council"}), timeout=25) as response:
        data = response.read(250001)
    if len(data) > 250000:
        raise ValueError("download exceeds the frozen bound")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    dest = parser.parse_args().output.resolve()
    if not dest.is_relative_to(Path.cwd().resolve() / "build"):
        raise ValueError("output must be under the checkout build directory")
    dest.mkdir(parents=True, exist_ok=False)

    compact = archive(ASSEMBLER)
    if sha256(compact).hexdigest() != "39758f147a8e615f8c77586ce3c85a25c6728910a86612eea184fc86eb606992":
        raise ValueError("published Raspberry Pi release SHA-256 differs")
    with tarfile.open(fileobj=io.BytesIO(compact), mode="r:gz") as contents:
        data = contents.extractfile("pioasm/pioasm").read(425001)
        if len(data) != 422960:
            raise ValueError("unexpected assembler size")
        (dest / "pioasm").write_bytes(data)
        (dest / "pioasm").chmod(0o755)
    result = {"assembler_archive": {"url": ASSEMBLER, "bytes": len(compact),
                                    "sha256": sha256(compact).hexdigest()},
              "assembler_binary_sha256": sha256(data).hexdigest()}

    compact = archive(EMULATOR)
    expected = "9ExR1cgmnU6bx06Bz0Lty0OH/y+lRN+s0tJKA/fnz6lJt7Cpcci/AXmQy0C5FE3y5J0f+f6f2Qbnr/zrX0JwOw=="
    if sha512(compact).digest() != base64.b64decode(expected):
        raise ValueError("published npm archive SHA-512 differs")
    result["emulator_archive"] = {"url": EMULATOR, "bytes": len(compact), "sha512_base64": expected,
                                "source_commit": "cab5fae8d72f44dc300dc139fb6e600f95e8031e"}
    files = {}
    with tarfile.open(fileobj=io.BytesIO(compact), mode="r:gz") as contents:
        for member in contents.getmembers():
            path = PurePosixPath(member.name)
            if not member.isfile() or path.parts[:3] != ("package", "dist", "cjs"):
                continue
            if path.suffix != ".js" and path.name != "package.json":
                continue
            if ".." in path.parts or member.size > 150000:
                raise ValueError("unexpected packaged module")
            local = dest / "cjs" / Path(*path.parts[3:])
            local.parent.mkdir(parents=True, exist_ok=True)
            data = contents.extractfile(member).read(member.size)
            local.write_bytes(data)
            files[path.as_posix()] = sha256(data).hexdigest()
    result["emulator_members"] = files
    (dest / "tools.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{len(files)} emulator modules extracted; assembler and emulator digests match")


if __name__ == "__main__":
    main()
