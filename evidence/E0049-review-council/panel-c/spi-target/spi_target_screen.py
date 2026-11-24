"""Score externally generated SPI-mode-0 command/reply traffic at G4 ports."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from selector_orders import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES, checked, execute, memory_file, sha
from resident_replay import G4, released

REPLIES={0xa4:0x3c,0xa5:0xa7}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def make_plan(repo,source,out,name):
    tool=out/"release-assembler.py"
    if not tool.exists():
        tool.write_bytes(released(repo,"tools/assembler.py"))
    spec=importlib.util.spec_from_file_location("frozen_assembler",tool)
    assembler=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembler)
    image=assembler.assemble(source)
    plan=assembler.load_plan(image)
    rows=[]
    for step in plan["steps"]:
        e=step["expected"]
        flush=step["action"]=="flush_idle"
        rows.append("%d %d %02x %02x %02x %d %02x %d %02x %d" %
            (step["rst_n"],step["host_drives_uio"],0xe7 if flush else step["ui_in"],step["uio_in"],
             e["uio_oe"],"uio_out" in e,e.get("uio_out",0),"uo_out" in e,e.get("uo_out",0),flush))
    (out/(name+".plan")).write_text("\n".join(rows)+"\n")
    return {"words":len(image["words"]),"bytes":len(image["words"])*4,"binary_sha256":image["binary_sha256"],
            "clocked_load_steps":len(rows),"plan_sha256":sha(("\n".join(rows)+"\n").encode()),
            "payloads":image["payloads"],"step_counts":dict(Counter(step["action"] for step in plan["steps"]))}


def observe(raw):
    records={"O":[],"R":[],"F":[],"CS":[],"TERM":[],"MISSING":[],"END":[],"LOAD":[]}
    for line in raw.decode().splitlines():
        words=line.split()
        if not words or words[0] not in records:
            continue
        tag=words[0]
        if tag=="O":
            row=[int(words[1]),int(words[2],16),int(words[3],16)]
        elif tag=="R":
            row=[int(w) for w in words[1:4]]+[int(w,16) for w in words[4:]]
        elif tag in ("TERM","END"):
            row=[int(words[1])]+([int(words[2]),int(words[3],16)] if tag=="TERM" else [int(w,16) for w in words[2:]])
        else:
            row=[int(w) for w in words[1:]]
        records[tag].append(row)
    return records


class Rejection(ValueError):
    pass


def require(condition,reason):
    if not condition:
        raise Rejection(reason)


def score(records,opcode,kind,steps):
    changes, rises, falls=records["O"],records["R"],records["F"]
    require(records["LOAD"]==[[steps]],"loader count")
    require(len(records["TERM"])==len(records["END"])==1,"missing or repeated terminal")
    terminal,marker,status=records["TERM"][0]
    finish,final_status,final_oe,final_pads=records["END"][0]
    require(status>>6==2 and final_status==status and final_oe==0x30 and ((final_pads>>4)&3)==marker,
            "terminal ownership or unstable outcome")
    require(changes and not changes[0][1] and all(not(oe&0xc7) for _,oe,_ in changes),"target drove non-output")
    require(len(rises)==16 or kind==4,"requester edge count")
    sampled=sum(mosi<<(7-index) for _,index,mosi,_,_ in rises[:8])
    require(sampled==opcode if kind!=4 else sampled==opcode,"requester command evidence")
    activity=next((a[0] for a in changes if a[1]&8),None)
    if kind in (1,2):
        origin=records["MISSING"][0][0] if kind==1 else records["CS"][0][0]
        require(marker==3 and activity is None and 0<terminal-origin<=2000,"missing/late clock handling")
        require(any(r[0]>terminal for r in rises),"late edges not exercised")
        return {"outcome":"TIMEOUT","from_last_activity_ns":terminal-origin}
    if kind==3 or opcode not in REPLIES:
        require(marker==2 and activity is None,"bad opcode or early CS drove reply")
        if kind==3:
            origin=next(t for t,level in records["CS"] if level==1)
            require(terminal>=origin,"early CS not causal")
            return {"outcome":"BAD_CS","after_cs_ns":terminal-origin}
        first=next(i for i in range(7) if ((opcode ^ 0xa4) >> (7-i)) & 1)
        lag=terminal-rises[first][0]
        require(0<=lag<rises[first+1][0]-rises[first][0],"mismatched opcode did not reject at first differing bit")
        return {"outcome":"BAD_OPCODE","first_bad_command_bit":first,"decision_after_rise_ns":lag}
    require(len(falls)>=8 and activity is not None and activity>=falls[7][0],"MISO active prematurely or absent")
    require(all(not(oe&8) for _,i,_,oe,_ in rises if i<8),"driven command sample")
    if kind==4:
        cs=next(t for t,level in records["CS"] if level)
        require(rises[8][3]&8 and marker in (2,3),"abort did not interrupt driven MISO")
        released=next(t for t,oe,_ in changes if t>=cs and not(oe&8))
        return {"outcome":"ABORT","miso_release_ns":released-cs,"terminal_after_cs_ns":terminal-cs,"marker":marker,
                "passes_160ns_abort_limit":released-cs<=160}
    require(marker==1,"accepted opcode missing OK halting marker")
    expected=REPLIES[opcode]
    setup_margins=[]; hold_margins=[]; decoded=0
    # Evaluate every MISO state transition, in addition to the actual requester pin sample.
    train=[]
    for when,oe,out in changes:
        state=(out>>3)&1 if oe&8 else None
        if not train or state!=train[-1][1]:
            train.append((when,state))
    for when,index,_,oe,pads in rises[8:]:
        bit=index-8
        wanted=(expected>>(7-bit))&1
        actual=(pads>>3)&1
        if not(oe&8) or actual!=wanted:
            raise Rejection(f"reply bit {bit}: expected {wanted}, sampled {actual}, driven {bool(oe&8)}")
        before=[(t,v) for t,v in train if t<=when]
        after=[(t,v) for t,v in train if t>when]
        require(before and before[-1][1]==wanted and after,"incomplete response levels")
        setup=when-before[-1][0]; hold=after[0][0]-when
        require(setup>=60 and hold>=40,"reply setup or hold")
        setup_margins.append(setup); hold_margins.append(hold)
        decoded=(decoded<<1)|actual
    last=falls[-1][0]
    release=next(t for t,v in train if t>=last and v is None)
    require(release-last<=160,"normal MISO release")
    require(terminal>=next(t for t,level in records["CS"] if level),"early success before deselect")
    return {"outcome":"OK","reply":decoded,"min_miso_setup_ns":min(setup_margins),"min_miso_hold_ns":min(hold_margins),
            "miso_release_after_last_fall_ns":release-last}


def cases(full):
    if full:
        for opcode in range(256):
            yield f"all-{opcode:02x}",opcode,500,7,0,"normal",None
        for opcode in REPLIES:
            for h in (250,500,1000):
                for phase in (1,7,13,19):
                    yield f"rate-{opcode:02x}-{h}-{phase}",opcode,h,phase,0,"normal",None
            yield f"uneven-{opcode:02x}",opcode,500,13,5,"normal",None
    else:
        for opcode in REPLIES:
            yield f"all-{opcode:02x}",opcode,500,7,0,"normal",None
    for row in [("named-bad",0x24,500,7,0,"normal",None),("missing",0xa5,500,13,1,"normal",None),
                ("late",0xa4,500,1,2,"normal",None),("early-cs",0xa5,500,19,3,"normal",None),
                ("abort",0xa5,250,7,4,"normal",None),("reply-mutation",0xa5,500,7,0,"mutant","reply bit 7")]:
        yield row


def run_matrix(impl,compiled,images,out):
    stage=out/impl; stage.mkdir()
    matrix={}; counts=Counter(); failures=[]
    for name,opcode,half,phase,kind,image,negative in cases(impl=="rtl"):
        command=["vvp",compiled,f"+plan={out}/{image}.plan",f"+rows={images[image]['clocked_load_steps']}",
                 f"+opcode={opcode}",f"+phase={phase}",f"+half={half}",f"+kind={kind}"]
        proc=subprocess.run(command,capture_output=True,timeout=20)
        raw=proc.stdout+proc.stderr
        decoded=None
        try:
            require(proc.returncode==0,"simulation exit "+str(proc.returncode))
            decoded=score(observe(raw),opcode,kind,images[image]["clocked_load_steps"])
            require(not negative,"mutated reply unexpectedly passed")
            counts[decoded["outcome"]]+=1
        except (Rejection,ValueError,StopIteration,IndexError) as error:
            reason=str(error) or type(error).__name__
            intended=negative is not None and reason.startswith(negative)
            decoded={"outcome":"REJECTED_MUTATION" if intended else "UNEXPECTED_FAILURE","reason":reason}
            counts[decoded["outcome"]]+=1
            if not intended: failures.append(name)
        matrix[name]=decoded
        if (name in ("all-a4","all-a5","named-bad","missing","late","early-cs","abort","reply-mutation","uneven-a4")
                or (failures and name==failures[0])):
            (stage/(name+".log.gz")).write_bytes(gzip.compress(raw,mtime=0))
    canonical=(json.dumps(matrix,sort_keys=True,separators=(",",":"))+"\n").encode()
    (stage/"cases.json.gz").write_bytes(gzip.compress(canonical,mtime=0))
    oks=[r for r in matrix.values() if r["outcome"]=="OK"]
    rejected=[r for r in matrix.values() if r["outcome"]=="BAD_OPCODE"]
    return {"cases":len(matrix),"outcomes":dict(counts),"unexpected_failures":failures,
            "first_unexpected":({failures[0]:matrix[failures[0]]} if failures else None),
            "first_bad_command_index_histogram":dict(Counter(r["first_bad_command_bit"] for r in rejected)),
            "minimum_modeled_setup_ns":min((r["min_miso_setup_ns"] for r in oks),default=None),
            "minimum_modeled_hold_ns":min((r["min_miso_hold_ns"] for r in oks),default=None),
            "maximum_normal_release_ns":max((r["miso_release_after_last_fall_ns"] for r in oks),default=None),
            "named":{n:matrix[n] for n in ("all-a4","all-a5","named-bad","missing","late","early-cs","abort","reply-mutation")},
            "canonical_sha256":sha(canonical)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--pdk-libs",type=Path,required=True)
    args=parser.parse_args()
    repo,out,pdk=args.repo.resolve(),args.out.resolve(),args.pdk_libs.resolve()
    out.mkdir(exist_ok=False,parents=True)
    result={"started_utc":stamp(),"status":"INCOMPLETE","implementation":{}}
    try:
        source=(HERE/"spi_test_target.asm").read_text(encoding="utf-8")
        mutation=source.replace(".data TX1 0xa7",".data TX1 0xa6")
        if source==mutation: raise ValueError("ineffective mutation")
        result["source_sha256"]={p.name:sha(p.read_bytes()) for p in
                [Path(__file__),HERE/"spi_test_target.asm",HERE/"spi_target_tb.v",HERE/"spi-target-contract.md"]}
        images={tag:make_plan(repo,text,out,tag) for tag,text in [("normal",source),("mutant",mutation)]}
        result["images"]=images
        result["release_assembler_sha256"]=sha((out/"release-assembler.py").read_bytes())
        result["simulator"]=execute(["iverilog","-V"],out).decode().splitlines()[0]
        lock=json.loads(released(repo,"tools/production-profile.json"))
        result["release_source"]=G4; result["qualified_file_sha256"]={}
        archive=repo/ARCHIVE; checked(archive.read_bytes(),ARCHIVE_SHA,ARCHIVE)
        result["g4_archive_sha256"]=ARCHIVE_SHA
        result["g4_netlist_sha256"]=NETLIST_SHA
        with ZipFile(archive) as zipped, ExitStack() as stack:
            def ram(name,raw): return stack.enter_context(memory_file(name,raw))
            rtl=[]; models=[]
            for name,wanted in lock["files_sha256"].items():
                if name.startswith("src/") and name.endswith(".v"):
                    rtl.append(ram(name.split("/")[-1],checked(zipped.read(name),wanted,name)))
                    result["qualified_file_sha256"][name]=wanted
            for name,wanted in lock["model_sha256"].items():
                data=gzip.decompress(released(repo,f"evidence/E0042-sram-prefetch-screen/feasibility/verilog/{name}.gz"))
                models.append(ram(name,checked(data,wanted,name)))
                result["qualified_file_sha256"][name]=wanted
            if len(rtl)!=5 or len(models)!=2: raise ValueError("source count")
            nl=ram("g4.v",checked(zipped.read("tt_submission/tt_um_khangelani_protocol_emulator.v"),NETLIST_SHA,"netlist"))
            for name,wanted in PDK_FILES.items(): checked((pdk/name).read_bytes(),wanted,name)
            result["cell_library_sha256"]=PDK_FILES
            for impl,files in [("rtl",rtl+models),("g4_netlist",[nl,*models,*(pdk/n for n in PDK_FILES)])]:
                with memory_file("spi-target.vvp") as compiled:
                    execute(["iverilog","-g2012","-DFUNCTIONAL","-DSYNTHESIS","-DSIM","-s","spi_target_tb",
                             "-o",compiled,HERE/"spi_target_tb.v",*files],out)
                    result["implementation"][impl]=run_matrix(impl,compiled,images,out)
        result["status"]="COMPLETE_DIGITAL_SCREEN"
        if any(r["unexpected_failures"] for r in result["implementation"].values()):
            result["status"]="COMPLETE_WITH_UNEXPECTED_FAILURES"
        result["stronger_abort_pass"]=all(r["named"]["abort"].get("passes_160ns_abort_limit",False)
                                         for r in result["implementation"].values())
    except Exception as exc:
        result["failure"]=str(exc)
        raise
    finally:
        result["ended_utc"]=stamp()
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"],"stronger_abort_pass",result["stronger_abort_pass"])


if __name__=="__main__":
    main()
