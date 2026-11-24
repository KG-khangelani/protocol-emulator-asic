"""Exercise four external MISO topologies against one actual SRAM image."""
from collections import Counter
from contextlib import ExitStack
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile


SOURCE = Path(__file__).resolve().parent
ARCH = Path("evidence/E0047-g4-submission-candidate/ci-43543626249")
PDK_REV = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"
PDK = Path("/pdk/ciel/ihp-sg13/versions")/PDK_REV/"ihp-sg13cmos5l/libs.ref"
MODELS = Path("evidence/E0042-sram-prefetch-screen/feasibility/verilog")
NAMES = ("direct","one_way","bilateral","disarmed")
SCHEDULES = ("normal_a5","parked_high","new_mode0_a4")
PLAN_SHA = "16f016a699ee92431bede9995e396d23af35e4f5f83998bf64a22438b47811a9"
PDK_MODELS = {"sg13cmos5l_io/verilog/sg13cmos5l_io.v":"ae986803821a9d6c3af9c221c33c3aa58ca23c283d3ad93ed4b3a2c45d6ccb4d",
              "sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v":"5491a3edf7468792b5222e7abe057e0583a407c01b2086d4fd44a55b6cf88055",
              "sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v":"485945f1b167daa68354548f46c95bdbff7d931516fc5b4edd47f2e2cd555735"}


def checked(data, wanted, what):
    if sha256(data).hexdigest() != wanted:
        raise ValueError(f"unexpected source digest {what}")
    return data


def memory_file(stack, name, payload=b""):
    stream = stack.enter_context(os.fdopen(os.memfd_create(name),"w+b"))
    stream.write(payload)
    stream.flush()
    return f"/proc/{os.getpid()}/fd/{stream.fileno()}"


def execute(args):
    result = subprocess.run(args,capture_output=True,text=True,timeout=90)
    if result.returncode:
        raise ValueError(f"{args[0]} failed\n{result.stdout[-1300:]}\n{result.stderr[-1300:]}")
    return result.stdout


def observations(raw):
    snapshots = {}
    edges = {0:[], 1:[]}
    for line in raw.splitlines():
        tokens=line.split()
        if not tokens:
            continue
        if tokens[0]=="SV":
            label, when, cs,sck,internal,value,branch,peer_on,peer_value,bus,status = tokens[1:]
            snapshots[label] = {"time_ns":int(when),"cs":cs,"sck":sck,"chip_oe":internal,"chip_value":value,
                                "branch_oe":branch,"peer_on":peer_on,"peer_value":peer_value,"bus":bus,"status":status}
        elif tokens[0]=="EDGE":
            first,bit,internal,branch,bus,status=tokens[1:]
            edges[int(first)].append((int(bit),internal,branch,bus,status))
    if len(edges[1]) not in (9,16) or "terminal" not in snapshots:
        raise ValueError("incomplete event records")
    return snapshots, edges


def frame_summary(edges):
    if not edges:
        return None
    command_drive = [i for i,_,drive,_,_ in edges if i<8 and drive=="1"]
    response = [data if drive=="1" else "z" for i,_,drive,data,_ in edges if i>=8]
    return {"command_driven_indices":command_drive,"response_bits":''.join(response)}


def assert_expected(mode, schedule, polarity, snapshots, edges):
    c = snapshots["command_drive_control"]
    assert c["chip_oe"] == "0"
    if mode == 1:
        assert c["branch_oe"] == "1" and c["bus"]=="x"
    else:
        assert c["branch_oe"] == "0" and c["bus"]=="1"
    if schedule==0:
        assert frame_summary(edges[1])["response_bits"] == "10100111"
        return
    after, before = snapshots["abort_plus_1"], snapshots["abort_plus_159"]
    assert after["chip_oe"]=="1" and after["chip_value"]=="1"
    assert before["time_ns"]-after["time_ns"]==158
    if mode==0:
        assert after["branch_oe"]=="1" and after["bus"]==("1" if polarity else "x")
    else:
        assert after["branch_oe"]=="0" and after["bus"]==str(polarity)
    if schedule==1:
        early = snapshots["reselect_with_peer"]
        assert early["time_ns"]-after["time_ns"]==160
        if mode==3:
            assert early["branch_oe"]=="0"
        else:
            assert early["chip_oe"]=="1" and early["branch_oe"]=="1"
            assert early["bus"] == ("1" if polarity else "x")
    if schedule==2:
        second=frame_summary(edges[0])
        assert len(edges[0])==16 and second["response_bits"]!="00111100"
        if mode==3:
            assert not second["command_driven_indices"] and second["response_bits"]=="zzzzzzzz"


def run():
    frozen=json.loads((ARCH/"result.json").read_bytes())
    index=json.loads((ARCH/"zip-files.json").read_bytes())
    archive_ref=frozen["archives"]["tt_submission"]
    archive=ARCH/f"{archive_ref['id']}.zip"
    plan=SOURCE/"switch-normal.plan"
    checked(plan.read_bytes(),PLAN_SHA,plan)
    compile_version=execute(["iverilog","-V"]).splitlines()[0]
    checked(archive.read_bytes(),archive_ref["sha256"],archive)
    for file,expected in PDK_MODELS.items():
        checked((PDK/file).read_bytes(),expected,file)
    outputs={}
    with ExitStack() as stack:
        archive=stack.enter_context(ZipFile(archive))
        rtl=[]; models=[]
        for name,expected in frozen["candidate"]["source_sha256"].items():
            member="src/"+name
            rtl.append(memory_file(stack,name,checked(archive.read(member),expected,member)))
        for name,expected in frozen["candidate"]["model_sha256"].items():
            models.append(memory_file(stack,name,checked(gzip.decompress((MODELS/(name+".gz")).read_bytes()),expected,name)))
        member="tt_submission/tt_um_khangelani_protocol_emulator.v"
        nl=memory_file(stack,"g4.v",checked(archive.read(member),index["tt_submission"][member],member))
        for implementation,files in (("rtl",rtl+models),("g4",[nl,*models,*(PDK/n for n in PDK_MODELS)])):
            compiled=memory_file(stack,implementation+".vvp")
            execute(["iverilog","-g2012","-DFUNCTIONAL","-DSYNTHESIS","-DSIM","-s","switch_reselect_tb",
                     "-o",compiled,SOURCE/"switch_reselect_tb.sv",*files])
            records={}
            for mode,name in enumerate(NAMES):
                for kind,schedule in enumerate(SCHEDULES):
                    for polarity in ((0,) if kind==0 else (0,1)):
                        text=execute(["vvp",compiled,f"+mode={mode}",f"+schedule={kind}",f"+same_peer={polarity}",
                                      f"+plan={plan}"])
                        snaps,edges=observations(text)
                        try:
                            assert_expected(mode,kind,polarity,snaps,edges)
                        except AssertionError as exc:
                            raise ValueError(f"{implementation}/{name}/{schedule}/peer{polarity}\n"+text) from exc
                        records[f"{name}/{schedule}/peer{polarity}"]={"snapshots":snaps,"first_frame":frame_summary(edges[1]),
                                                                     "second_frame":frame_summary(edges[0])}
            outputs[implementation]=records
    if outputs["rtl"]!=outputs["g4"]:
        raise ValueError("RTL and submitted gate observations differ")
    return {"scope":"fresh zero-delay RTL and G4 gate functional models; all external selectable paths ideal digital elements",
            "simulator":compile_version,"archive_sha256":archive_ref["sha256"],"submitted_netlist_sha256":frozen["netlist_sha256"],
            "input_plan_sha256":PLAN_SHA,"input_plan_steps":498, "assembly_image_sha256":"8d257ace7cc236c3ff5b2b71242679422f81900b6ee10dbd0daa78a7f318a81e",
            "source_sha256":{p:sha256((SOURCE/p).read_bytes()).hexdigest() for p in ("switch_reselect_tb.sv","switch_reselect.py")},
            "pdk_source":PDK_REV,"cell_models":PDK_MODELS,
            "representations":["rtl","g4"],"matched_cases_per_representation":len(outputs["g4"]),"cases":outputs["g4"]}


if __name__=="__main__":
    print(json.dumps(run(),indent=2))
