"""Read both published starter READMEs via bounded public ZIP prefixes and hash the notice."""
import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(url, count, *, partial=False):
    headers = {"User-Agent":"protocol-emulator-council", "Cache-Control":"no-cache"}
    if partial:
        headers["Range"] = f"bytes=0-{count-1}"
    with urlopen(Request(url, headers=headers),timeout=45) as response:
        data = response.read(count if partial else count + 1)
        if not partial and len(data)>count:
            raise ValueError("notice exceeds cap")
        return data, {"http":response.status,"content_range":response.headers.get("Content-Range"),
                      "bytes_read":len(data),"url":url}


def prefix_readme(blob):
    offset = 0
    while offset+30 <= len(blob):
        fields = struct.unpack_from("<4s5H3L2H",blob,offset)
        sig, _, flags, method, _, _, _, packed, size, namesize, extrasize = fields
        if sig != b"PK\x03\x04" or flags & 8 or method != 0 or packed != size:
            raise ValueError("unexpected ZIP member/header")
        name = blob[offset+30:offset+30+namesize].decode("utf-8")
        start = offset+30+namesize+extrasize
        end = start+size
        if end>len(blob):
            raise ValueError("README outside prefix")
        if name=="README.md":
            return blob[start:end],start
        offset = end
    raise ValueError("missing README")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(exist_ok=False,parents=True)
    result={"started_utc":datetime.now(timezone.utc).isoformat(),"status":"INCOMPLETE","releases":{}}
    notice="https://blog.janestreet.com/protocol-emulator-asic-competition/"
    try:
        page,error=fetch(notice,196608)
        result["notice"]=dict(error,sha256=digest(page))
        old=json.loads((args.repo/"docs/research/rule-reviews/2026-11-24.json").read_bytes())
        result["notice"]["matches_retained_html"]=result["notice"]["sha256"]==old["retrieval"]["sha256"]
        g4=args.repo/"evidence/E0047-g4-submission-candidate/publication/g4-submission.json"
        g5=args.repo/"evidence/E0048-waveform-replay/publication/downloaded/g5-waveform-replay.zip"
        with ZipFile(g5) as source:
            g5_sha=digest(source.read("README.md"))
        for tag,asset,wanted in [("v0.1.0","g4-submission-bundle.zip",json.loads(g4.read_bytes())["bundle_members_sha256"]["README.md"]),
                                 ("v0.1.1","g5-waveform-replay.zip",g5_sha)]:
            url=f"https://github.com/KG-khangelani/protocol-emulator-asic/releases/download/{tag}/{asset}"
            prefix,stamp=fetch(url,32768,partial=True)
            text,start=prefix_readme(prefix)
            actual=digest(text)
            if actual!=wanted:
                raise ValueError(f"{tag} README does not match its retained member")
            (args.out/(tag+"-README.md")).write_bytes(text)
            result["releases"][tag]=dict(stamp,readme_size=len(text),readme_start=start,
                                         readme_sha256=actual,matched_retained_member=True)
        result["status"]="PASS_PUBLIC_README_CHECK"
    except Exception as exc:
        result["error"]=str(exc)
        raise
    finally:
        result["ended_utc"]=datetime.now(timezone.utc).isoformat()
        (args.out/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["status"])


if __name__=="__main__":
    main()
