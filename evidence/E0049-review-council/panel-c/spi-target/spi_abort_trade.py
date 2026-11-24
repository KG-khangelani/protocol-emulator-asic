"""Measure the single-wait timeout trade and assemble a bounded CS/SCK polling alternative."""
import argparse
import gzip
import importlib.util
import json
import sys
from contextlib import ExitStack
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from spi_target_screen import G4, ARCHIVE, ARCHIVE_SHA, checked, execute, make_plan, memory_file, observe, released, score, sha, stamp, Rejection


def replace_response_timeout(original,delay):
    anchor="    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad\n    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout\nfinish_"
    if original.count(anchor)!=2:
        raise ValueError("response wait anchors changed")
    return original.replace(anchor,anchor.replace("timeout=DEADLINE",f"timeout={delay}"))


def cooperative_source(original):
    prefix=original.split("\nreply_a:\n",1)[0]
    parts=[("command",prefix)]
    for label,reply in (("a",0x3c),("b",0xa7)):
        lines=[f"reply_{label}:","    WAIT_PIN pin=0 level=0 timeout=DEADLINE on_timeout=timeout"]
        previous=None
        for i in range(8):
            bit=(reply>>(7-i))&1
            if bit!=previous:
                lines.append(f"    SET mask=8 value={bit*8} oe=8")
            previous=bit
            for desired in (1,0):
                stem=f"{label}{i}_{desired}"
                lines.extend([f"    LOOP count=37 end={stem}_expired",
                              "    WAIT_PIN pin=2 level=0 timeout=0 on_timeout=bad",
                              f"    WAIT_PIN pin=0 level={1-desired} timeout=0 on_timeout={stem}_seen",
                              f"{stem}_expired:","    SET mask=0x38 value=0x30 oe=0x30","    HALT",
                              f"{stem}_seen:"])
        lines.extend(["    SET mask=8 value=0 oe=0","    WAIT_PIN pin=2 level=1 timeout=DEADLINE on_timeout=timeout",
                      "    SET mask=0x30 value=0x10 oe=0x30","    HALT"])
        parts.append(("reply_"+label,"\n".join(lines)))
    parts.append(("cleanup","bad:\n    SET mask=0x38 value=0x20 oe=0x30\n    HALT\ntimeout:\n    SET mask=0x38 value=0x30 oe=0x30\n    HALT"))
    sections={k:sum(1 for line in s.splitlines() if line.startswith("    ")) for k,s in parts}
    return "\n\n".join(text for _,text in parts)+"\n", sections


def simulation(compiled,plan,steps,phase,half,kind,out):
    raw=execute(["vvp",compiled,f"+plan={plan}",f"+rows={steps}","+opcode=165",
                 f"+phase={phase}",f"+half={half}",f"+kind={kind}"],out)
    rec=observe(raw)
    if kind==4:
        cs=next(t for t,v in rec["CS"] if v)
        status=[(t,oe) for t,oe,_ in rec["O"] if t<=cs]
        if not(status[-1][1]&8):
            return {"outcome":"ALREADY_RELEASED_BEFORE_CS","last_oe_change_minus_cs_ns":status[-1][0]-cs}
    try:
        return score(rec,0xa5,kind,steps)
    except (ValueError,IndexError,StopIteration) as error:
        return {"outcome":"FAIL","reason":str(error) or type(error).__name__,"terminal":rec["TERM"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    repo,out=args.repo.resolve(),args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    original=(HERE/"spi_test_target.asm").read_text(encoding="utf-8")
    result={"started_utc":stamp(),"status":"INCOMPLETE","release":G4}
    try:
        lock=json.loads(released(repo,"tools/production-profile.json"))
        archive=repo/ARCHIVE
        checked(archive.read_bytes(),ARCHIVE_SHA,ARCHIVE)
        rows={}
        with ZipFile(archive) as zipped, ExitStack() as stack:
            sources=[]
            for name,wanted in lock["files_sha256"].items():
                if name.startswith("src/") and name.endswith(".v"):
                    raw=checked(zipped.read(name),wanted,name)
                    sources.append(stack.enter_context(memory_file(name.split("/")[-1],raw)))
            for name,wanted in lock["model_sha256"].items():
                data=gzip.decompress(released(repo,f"evidence/E0042-sram-prefetch-screen/feasibility/verilog/{name}.gz"))
                sources.append(stack.enter_context(memory_file(name,checked(data,wanted,name))))
            if len(sources)!=7: raise ValueError("source set")
            compiled=stack.enter_context(memory_file("diagnostic.vvp"))
            execute(["iverilog","-g2012","-DFUNCTIONAL","-DSYNTHESIS","-DSIM","-s","spi_target_tb","-o",compiled,
                     HERE/"spi_target_tb.v",*sources],out)
            for delay in range(81):
                variant=replace_response_timeout(original,delay)
                image=make_plan(repo,variant,out,"trial")
                if image["words"]!=59 or image["clocked_load_steps"]!=498:
                    raise ValueError("source edit changed the workload size")
                phases={str(phase):simulation(compiled,out/"trial.plan",498,phase,1000,0,out)
                        for phase in (1,7,13,19)}
                abort=simulation(compiled,out/"trial.plan",498,7,250,4,out)
                rows[delay]={"binary_sha256":image["binary_sha256"],"normal":phases,"abort":abort,
                             "all_slow_pass":all(o["outcome"]=="OK" for o in phases.values()),
                             "abort_pass":abort.get("passes_160ns_abort_limit",False)}
        if rows[80]["abort"].get("miso_release_ns")!=1563 or not rows[80]["all_slow_pass"]:
            raise ValueError("original condition did not reproduce")
        if rows[80]["binary_sha256"]!="8d257ace7cc236c3ff5b2b71242679422f81900b6ee10dbd0daa78a7f318a81e":
            raise ValueError("original firmware identity")
        canonical=(json.dumps(rows,sort_keys=True,separators=(",",":"))+"\n").encode()
        (out/"sweep.json.gz").write_bytes(gzip.compress(canonical,mtime=0))
        slow=[d for d,r in rows.items() if r["all_slow_pass"]]
        fast=[d for d,r in rows.items() if r["abort_pass"]]
        result["single_timeout"]={"operands":len(rows),"individual_simulations":5*len(rows),
               "all_four_500kHz_phases_pass":slow,"active_abort_within_160ns":fast,
               "both":[d for d in slow if d in fast],"canonical_sha256":sha(canonical),
               "boundary":{str(d):rows[d] for d in sorted(({0,80,min(slow),min(slow)-1,min(fast),max(fast),max(fast)+1})) if d in rows}}
        alt,sections=cooperative_source(original)
        (out/"cooperative.asm").write_text(alt)
        spec=importlib.util.spec_from_file_location("frozen_compile",out/"release-assembler.py")
        assembler=importlib.util.module_from_spec(spec); spec.loader.exec_module(assembler)
        try:
            image=assembler.assemble(alt)
        except ValueError as failure:
            result["cooperative"]={"assembled":False,"error":str(failure),"section_words":sections,
                                   "total_source_words":sum(sections.values()),"source_sha256":sha(alt.encode())}
        else:
            result["cooperative"]={"assembled":True,"words":len(image["words"]),"source_sha256":sha(alt.encode())}
        result["status"]="COMPLETE_BOUND_DIAGNOSTIC"
    except Exception as error:
        result["error"]=str(error)
        raise
    finally:
        result["ended_utc"]=stamp()
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"],result["single_timeout"]["both"],result["cooperative"])


if __name__=="__main__":
    main()
