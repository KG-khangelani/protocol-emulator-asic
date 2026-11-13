# SPDX-License-Identifier: Apache-2.0
"""Stage and audit the explicitly identified SRAM physical candidate in CI."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/i2c"))
from tools import physical_candidate as common, physical_g2
from build_sram_candidate import build
from prepare_sram_physical import power_rectangles, pdn_script
from run_sram_mapping import blackbox, MACRO
from run_current_regression import INPUTS
from align_sram_magic import ALIGNED_SHA256, MAGIC_TREE_SHA256, NATIVE_DRC_SHA256, REFERENCE_SHA256

EVIDENCE = ROOT / "evidence/E0042-sram-prefetch-screen"
STAGING = ROOT / "build/sram-physical"
PLUGIN_FILES = (
    "librelane_plugin_sram.py", "sram_power_step.py", "connect_sram_power.py",
    "check_sram_power.tcl", "sram_input_buffers.tcl", "audit_sram_input_buffers.py",
)
GUARDED_PLUGIN_FILES = (*PLUGIN_FILES, "audit_sram_pin_power.py")
ALIGNED_PLUGIN_FILES = (*GUARDED_PLUGIN_FILES, "align_sram_magic.py", "sram_magicrc.tcl")
PORT_PLUGIN_FILES = (*ALIGNED_PLUGIN_FILES, "select_sram_power_ports.py", "sram_power_ports_step.py")
POWER_PORT_CONTRACT = {
    "step": "Project.SelectSramPowerPorts", "after": "Odb.CellFrequencyTables",
    "original_rectangles": 200, "removed_internal_rectangles": 146,
    "remaining_external_rectangles": 54, "minimum_width_dbu": 2100,
    "maximum_vertical_edge_distance_dbu": 10000,
    "preserve_all_non_pin_def_bytes_and_signal_pins": True,
}
SRAM_IMPORT_PATTERNS = ["lvsres_*", "*_CELL_SUB", "VIA_M1_*", "VIA_M2_*", "RSC_*", "*_CELL_CORNER", "*_BITKIT_CORNER"]
SRAM_IMPORT_SETUP_SHA256 = "5a818473a3ffad96d84e1f72331fbb94c46cc1df24a01bc9d8367ac3a7211cd7"
MODEL_SETS = {
    "nom_typ_1p20V_25C": "typ_1p20V_25C",
    "nom_fast_1p32V_m40C": "fast_1p32V_m55C",
    "nom_slow_1p08V_125C": "slow_1p08V_125C",
}
FAST_BOUNDARY = "Standard cells -40 C with vendor SRAM -55 C; not an isothermal SRAM characterization."
TEMPLATE_SHA256 = "64b52f2150f699edc7fb500c2f486a51eca66fd91d3efb7347200bd2cf83a2ee"
require, digest, read, write = common.require, common.digest, common.read_json, common.write_json


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def magic_alignment_contract():
    return {
        "step": "Magic.DRC", "original_tree_sha256": MAGIC_TREE_SHA256,
        "native_drc_script_sha256": NATIVE_DRC_SHA256,
        "changed_files": ALIGNED_SHA256.copy(), "reference_sha256": REFERENCE_SHA256.copy(),
        "background_checking_suspended_during_import_only": True,
    }


def candidate():
    return read(EVIDENCE / "candidate.json")


def mapped_macro_views():
    """Use the retained actual mapping inputs, including GDS and CDL identities."""
    index = read(EVIDENCE / "mapped/archive.json")
    archive = EVIDENCE / "mapped/mapping.tar.gz"
    require(digest(archive) == index["sha256"], "mapped archive changed")
    with tarfile.open(archive) as stream:
        raw = stream.extractfile("result.json").read()
    require(sha(raw) == index["files"]["result.json"], "mapped input manifest changed")
    observation = json.loads(raw)
    require(observation["candidate"] == candidate(), "mapped candidate differs")
    return {name.split("/libs.ref/sg13cmos5l_sram/", 1)[1]: metadata
            for name, metadata in observation["macro_views"].items()}


def portable_config(header_name, *, guarded=False, aligned=False, power_ports=False):
    require(not aligned or guarded, "Magic alignment requires the guarded construction")
    require(not power_ports or (guarded and aligned), "power-port selection requires guarded aligned construction")
    config = read(common.baseline_config())
    config.pop("//", None)
    base = "pdk_dir::libs.ref/sg13cmos5l_sram/"
    macro = {key: [base + folder + "/" + MACRO + "." + extension]
             for folder, extension, key in (("gds", "gds", "gds"),
                                            ("lef", "lef", "lef"), ("cdl", "cdl", "spice"))}
    macro.update(
        lib={corner: [base + "lib/" + MACRO + "_" + suffix + ".lib"]
             for corner, suffix in MODEL_SETS.items()},
        vh=["dir::" + header_name],
        instances={"store.program_memory": {"location": [20.16, 302.4], "orientation": "FS"}},
    )
    config.update(
        meta={"flow": "SramBufferedClassic"}, MACROS={MACRO: macro}, OPENROAD_THREADS=4,
        PDN_CFG="dir::sram_pdn.tcl", SRAM_POWER_MANIFEST="dir::sram-preparation.json",
        PDN_HORIZONTAL_HALO=0, PDN_VERTICAL_HALO=0, PDN_SKIPTRIM=True,
        PDN_MACRO_CONNECTIONS=["^store\\.program_memory$ VPWR VGND VDD! VSS!",
                               "^store\\.program_memory$ VPWR VGND VDDARRAY! VSS!"],
    )
    if guarded:
        config["meta"]["flow"] = "SramGuardedClassic"
        config["MAGIC_GDS_FLATGLOB"] = SRAM_IMPORT_PATTERNS.copy()
    if aligned:
        config["MAGICRC"] = "dir::../sram_magicrc.tcl"
    if power_ports:
        config["meta"]["flow"] = "SramPortsClassic"
    return config


def prepare(args):
    guarded = getattr(args, "guarded", False)
    aligned = getattr(args, "align_magic", False)
    power_ports = getattr(args, "power_ports", False)
    require(not aligned or guarded, "Magic alignment requires --guarded")
    require(not power_ports or (guarded and aligned), "power-port selection requires --guarded --align-magic")
    production_audit = None
    if getattr(args, "production", False):
        require(guarded and aligned and power_ports, "production requires every qualified physical addition")
        from tools.production_sram import verify as verify_production
        # Check the actual selected files before generation or any in-place copy.
        production_audit = verify_production(ROOT)
    plugin_files = PORT_PLUGIN_FILES if power_ports else ALIGNED_PLUGIN_FILES if aligned else GUARDED_PLUGIN_FILES if guarded else PLUGIN_FILES
    out = args.output.resolve()
    require(out.is_relative_to((ROOT / "build").resolve()) and not out.exists(),
            "new output under build/ required; preserve previous attempts")
    lock = common.candidate_lock()
    common.baseline_config()
    info = (ROOT / "info.yaml").read_text(encoding="utf-8")
    require(re.search(r'^\s{2}tiles: "8x4"\s', info, re.M), "metadata is not 8x4")
    require(re.search(r"^\s{2}clock_hz:\s+50000000\s", info, re.M), "metadata clock drift")
    ci = EVIDENCE / "ci-95120d8/verification.json"
    require(read(ci)["status"] == "PASS_AUDITED_SRAM_CI", "complete SRAM CI audit missing")
    require(read(EVIDENCE / "regression/result.json")["status"] == "PASS_SRAM_CURRENT_BOTH_SIMULATORS",
            "complete protocol regression missing")
    require(read(EVIDENCE / "mapped/verification.json")["status"] == "PASS_MATCHED_SRAM_MAPPED_SCREEN",
            "matched mapped audit missing")
    tracked = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                      cwd=ROOT, text=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if args.stage_ci:
        require(os.getenv("GITHUB_ACTIONS") == "true", "in-place staging is CI-only")
        require(Path(os.environ["GITHUB_WORKSPACE"]).resolve() == ROOT, "CI workspace differs")
        require(not tracked and head == os.environ["GITHUB_SHA"], "clean exact workflow revision required")
    manifest = build(out / "candidate")
    require(manifest == candidate(), "fresh candidate differs from audited SRAM candidate")
    workspace = ROOT if args.stage_ci else out / "workspace"
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    for name, expected in manifest["source_sha256"].items():
        source = out / "candidate/src" / name
        require(digest(source) == expected, "candidate source changed: " + name)
        shutil.copyfile(source, workspace / "src" / name)
    model = (out / "candidate/models" / (MACRO + ".v")).read_bytes()
    header = blackbox(model)
    require(header.count(b"`timescale 1ns/10ps\n") == 1, "unexpected synthesis header")
    header = header.replace(b"`timescale 1ns/10ps\n", b"")
    (workspace / "src" / (MACRO + ".vh")).write_bytes(header)
    views = mapped_macro_views()
    lef = gzip.decompress((EVIDENCE / "feasibility/lef" / (MACRO + ".lef.gz")).read_bytes())
    require(sha(lef) == views["lef/" + MACRO + ".lef"]["sha256"], "macro LEF changed")
    rectangles = power_rectangles(lef)
    script, columns = pdn_script(rectangles, core_bounded=guarded)
    (workspace / "src/sram_pdn.tcl").write_bytes(script)
    geometry = {
        "candidate": manifest,
        "power_rectangles": {name: [[str(v) for v in row] for row in rows]
                             for name, rows in rectangles.items()},
        "column_centres": {name: [str(v) for v in rows] for name, rows in columns.items()},
        "fast_model_boundary": FAST_BOUNDARY,
    }
    # Native OpenDB serializes wire creation order. Preserve VPWR then VGND,
    # exactly as in the retained trial, rather than sorting this geometry map.
    (workspace / "src/sram-preparation.json").write_text(
        json.dumps(geometry, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name in plugin_files:
        shutil.copyfile(ROOT / "experiments/i2c" / name, workspace / name)
    write(workspace / "src/config.json", portable_config(MACRO + ".vh", guarded=guarded, aligned=aligned, power_ports=power_ports))
    names = set(INPUTS) | {common.BASE_CONFIG_PATH, "tools/physical_sram.py", ".github/workflows/gds-sram.yaml",
                           "experiments/i2c/align_sram_magic.py",
                           "tools/workbench/toolchain.lock.json", "experiments/i2c/prepare_sram_physical.py",
                           "experiments/i2c/run_sram_mapping.py", "experiments/i2c/build_sram_candidate.py",
                           "experiments/i2c/sram_prefetch.py", "experiments/i2c/sram_program_store.v",
                           "docs/specs/g2-sram-official-qualification.md"}
    names.update("experiments/i2c/" + name for name in plugin_files)
    if guarded:
        names.add("docs/decisions/0045-correct-sram-import-and-public-pin-power-clearance.md")
    if aligned:
        names.add("docs/decisions/0046-align-magic-contact-rules-with-pinned-references.md")
    if power_ports:
        names.add("docs/decisions/0047-export-existing-full-height-supply-ports.md")
    if production_audit:
        profile = read(ROOT / "tools/production-profile.json")
        names.update({"tools/production_sram.py", "tools/production-profile.json",
                      ".github/workflows/gds.yaml", profile["decision"]})
        names.update(profile[key]["path"] for key in
                     ("qualification", "combined_regression", "normal_command_verification", "corrected_netlist_pair"))
    provenance = {}
    for name in sorted(names):
        target = out / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (ROOT / name).read_bytes()
        target.write_bytes(raw)
        provenance[name] = sha(raw)
    staged_names = ["src/" + name for name in manifest["source_sha256"]]
    staged_names += ["src/config.json", "src/sram_pdn.tcl", "src/sram-preparation.json",
                     "src/" + MACRO + ".vh", *plugin_files]
    record = {
        "status": "PREPARED_UNQUALIFIED_SRAM_PHYSICAL_CANDIDATE",
        "created_utc": datetime.now(timezone.utc).isoformat(), "variant": "od128-sram",
        "workflow_source_commit": head, "staged_in_ci": bool(args.stage_ci),
        "tracked_changes_before_staging": tracked, "candidate": manifest, "flow_lock": lock,
        "ci_audit_sha256": digest(ci), "template_sha256": TEMPLATE_SHA256,
        "original_config_sha256_lf": lock["config_sha256_lf"],
        "config_source_path": common.BASE_CONFIG_PATH,
        "metadata_sha256_lf": common.text_digest(ROOT / "info.yaml"),
        "staged_sha256": {name: digest(workspace / name) for name in staged_names},
        "provenance_sha256": provenance, "macro_views": views,
        "fast_model_boundary": FAST_BOUNDARY, "public_test_names": sorted(physical_g2.PUBLIC_TEST_MODULES),
        "physical": "NOT_EVALUATED", "production": "NOT_PROMOTED",
    }
    if production_audit:
        require(record["staged_sha256"] == production_audit["files_sha256"],
                "regenerated physical files differ from actual qualified production")
        record["production"] = production_audit
        record["status"] = "PREPARED_MATCHING_QUALIFIED_PRODUCTION"
    if guarded:
        record["guarded_flow"] = {"core_bounded_stripes": True, "fixed_public_pin_rectangles": 43,
                                  "metal4_minimum_spacing_um": 0.42,
                                  "vendor_import_setup_sha256": SRAM_IMPORT_SETUP_SHA256,
                                  "vendor_import_patterns": SRAM_IMPORT_PATTERNS.copy()}
    if aligned:
        record["magic_contact_alignment"] = magic_alignment_contract()
    if power_ports:
        record["power_port_selection"] = POWER_PORT_CONTRACT.copy()
    write(out / "inputs.json", record)
    print("PASS: actual production and staged inputs match qualified SRAM" if production_audit else
          "PASS: exact audited SRAM candidate staged; physical qualification pending")


def one_stage(run, step):
    matches = [path for path in run.glob("*/config.json")
               if read(path).get("meta", {}).get("step") == step]
    require(len(matches) == 1, "missing or duplicate stage: " + step)
    directory = matches[0].parent
    require((directory / "state_out.json").is_file(), "incomplete stage: " + step)
    return directory


def inspect_resolved(resolved, inputs, workspace):
    """Check the actual resolved files, rather than only the staged copies."""
    common.verify_run_configuration(resolved, common.candidate_lock())
    guarded = "guarded_flow" in inputs
    ports = "power_port_selection" in inputs
    flow = "SramPortsClassic" if ports else "SramGuardedClassic" if guarded else "SramBufferedClassic"
    require(resolved["meta"]["flow"] == flow and
            resolved["meta"].get("substituting_steps") is None, "unexpected flow substitutions")
    if ports:
        require(guarded and "magic_contact_alignment" in inputs and
                inputs["power_port_selection"] == POWER_PORT_CONTRACT, "power-port selection contract differs")
    if guarded:
        require(resolved["MAGIC_GDS_FLATGLOB"] == SRAM_IMPORT_PATTERNS, "vendor SRAM import patterns changed")
        setup = Path(resolved["PDK_ROOT"]) / resolved["PDK"] / "libs.tech/magic/read_sram_gds.tcl"
        require(digest(setup) == SRAM_IMPORT_SETUP_SHA256, "vendor SRAM import setup changed")
        require(not resolved.get("MAGIC_DRC_MAGLEFS"), "abstract macro views cannot replace complete GDS DRC")
    if "magic_contact_alignment" in inputs:
        require(guarded, "Magic alignment requires guarded construction")
        require(inputs["magic_contact_alignment"] == magic_alignment_contract(), "Magic alignment contract differs")
        path = Path(resolved["MAGICRC"])
        require(path.resolve() == (workspace / "sram_magicrc.tcl").resolve() and
                digest(path) == inputs["staged_sha256"]["sram_magicrc.tcl"], "resolved Magic startup differs")
        tech = Path(resolved["PDK_ROOT"]) / resolved["PDK"] / "libs.tech/magic/ihp-sg13cmos5l.tech"
        require(Path(resolved["MAGIC_TECH"]).resolve() == tech.resolve() and
                digest(tech) == REFERENCE_SHA256["libs.tech/magic/ihp-sg13cmos5l.tech"],
                "original Magic technology differs")
    for name in ("RUN_MAGIC_DRC", "MAGIC_DRC_USE_GDS", "ERROR_ON_MAGIC_DRC", "ERROR_ON_ILLEGAL_OVERLAPS",
                 "ERROR_ON_LVS_ERROR", "ERROR_ON_PDN_VIOLATIONS", "ERROR_ON_TR_DRC"):
        require(resolved[name] is True, "required acceptance check disabled: " + name)
    require(resolved["MAX_TRANSITION_CONSTRAINT"] is None and not resolved["RUN_POST_GRT_DESIGN_REPAIR"],
            "rejected diagnostic setting carried into qualification")
    sources = [Path(path) for path in resolved["VERILOG_FILES"]]
    expected_sources = inputs["candidate"]["source_sha256"]
    require(len(sources) == len(expected_sources) and
            {p.resolve() for p in sources} == {(workspace / "src" / n).resolve() for n in expected_sources},
            "resolved RTL paths differ from staged sources")
    require({p.name: digest(p) for p in sources} == expected_sources, "actual resolved RTL changed")
    for key, name in (("PDN_CFG", "sram_pdn.tcl"), ("SRAM_POWER_MANIFEST", "sram-preparation.json")):
        path = Path(resolved[key])
        require(path.resolve() == (workspace / "src" / name).resolve() and
                digest(path) == inputs["staged_sha256"]["src/" + name], "resolved construction input differs: " + key)
    require(digest(Path(resolved["FP_DEF_TEMPLATE"])) == TEMPLATE_SHA256, "actual template changed")
    require(set(resolved["MACROS"]) == {MACRO}, "unexpected macro set")
    macro = resolved["MACROS"][MACRO]
    require([Path(p).resolve() for p in macro["vh"]] == [(workspace / "src" / (MACRO + ".vh")).resolve()],
            "unexpected synthesis macro header")
    require(not macro.get("nl") and not macro.get("spef"), "unexpected macro netlist/parasitic override")
    require(macro["instances"] == {"store.program_memory": {"location": [20.16, 302.4], "orientation": "FS", "array": None}},
            "macro placement changed")
    actual_views = {}
    for key in ("gds", "lef", "spice"):
        require(len(macro[key]) == 1, "unexpected macro view count")
        path = Path(macro[key][0])
        actual_views[path.parent.name + "/" + path.name] = {"sha256": digest(path), "bytes": path.stat().st_size}
    require(set(macro["lib"]) == set(MODEL_SETS), "macro model sets differ")
    for corner, suffix in MODEL_SETS.items():
        require(len(macro["lib"][corner]) == 1, "unexpected timing library count")
        path = Path(macro["lib"][corner][0])
        require(path.name == MACRO + "_" + suffix + ".lib", "corner mapping changed")
        actual_views["lib/" + path.name] = {"sha256": digest(path), "bytes": path.stat().st_size}
    require(actual_views == inputs["macro_views"] == mapped_macro_views(), "actual macro views differ")
    return actual_views


def check_run(args):
    run, staging = args.run.resolve(), args.staging.resolve()
    inputs = read(staging / "inputs.json")
    require(inputs["staged_in_ci"] and inputs["candidate"] == candidate(), "CI staging identity missing")
    for name, expected in inputs["staged_sha256"].items():
        require(digest(ROOT / name) == expected, "staged physical input changed: " + name)
    lock = common.candidate_lock()
    pdk = read(run / "pdk.json")
    require((pdk["FLOW_VERSION"], pdk["PDK"], pdk["PDK_SOURCE"], pdk["PDK_VERSION"]) ==
            (lock["librelane"], lock["pdk"], lock["pdk_source"], lock["pdk_commit"]), "flow/PDK identity drift")
    support = subprocess.check_output(["git", "-C", str(ROOT / "tt"), "rev-parse", "HEAD"], text=True).strip()
    require(support == lock["support_tools_commit"], "support revision differs")
    resolved = read(run / "resolved.json")
    actual_views = inspect_resolved(resolved, inputs, ROOT)
    power = one_stage(run, "Project.ConnectSramPower")
    grid = one_stage(run, "Project.CheckSramPower")
    buffer = one_stage(run, "Project.BufferSramInputs")
    connection = read(power / "power-connections.json")
    require(connection["status"] == "PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING" and
            len(connection["added_rectangles"]) == 144, "power construction differs")
    require(connection["preparation_sha256"] == digest(ROOT / "src/sram-preparation.json"), "power manifest differs")
    require(connection["input_odb_sha256"] == digest(Path(read(power / "state_in.json")["odb"])),
            "power audit database differs")
    grid_metrics = read(grid / "state_out.json")["metrics"]
    for suffix in ("", "__net:VPWR", "__net:VGND"):
        require(grid_metrics["design__power_grid_violation__count" + suffix] == 0, "fresh grid check failed")
    audit = read(buffer / "connectivity-audit.json")
    require(audit["status"] == "PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY" and
            audit["added_buffers"] == 9, "native buffer audit failed")
    for side in ("before", "after"):
        state = read(buffer / ("state_in.json" if side == "before" else "state_out.json"))
        require(audit[side + "_odb_sha256"] == digest(Path(state["odb"])), "buffer audit database differs")
    pin_guard = None
    if "guarded_flow" in inputs:
        guard = one_stage(run, "Project.CheckPublicPinPower")
        pin_guard = guard / "pin-power-audit/result.json"
        checked = read(pin_guard)
        require(checked["status"] == "PASS_PUBLIC_PIN_POWER_GEOMETRY" and not checked["violations"] and
                len(checked["pins"]) == 43 and checked["metal4_minimum_spacing_dbu"] == 420,
                "fixed public pin/power geometry did not pass")
        before, after = read(guard / "state_in.json"), read(guard / "state_out.json")
        require(checked["odb_sha256"] == digest(Path(before["odb"])) and before["odb"] == after["odb"],
                "pin guard did not inspect the unchanged actual database")
    metrics = read(run / "final/metrics.json")
    review = common.inspect_physical_metrics(metrics)
    require(metrics.get("magic__illegal_overlap__count") == 0, "illegal overlaps not cleared")
    netlist = ROOT / "tt_submission/tt_um_khangelani_protocol_emulator.v"
    require(digest(netlist) == digest(run / "final/nl/tt_um_khangelani_protocol_emulator.nl.v"),
            "submission/final netlist mismatch")
    verify_macro_netlist(netlist)
    result = {
        "status": "PASS_PHYSICAL_METRICS_PRECHECK_AND_NETLIST_PENDING" if review["status"] == "PASS"
                  else "PHYSICAL_METRICS_FAILED",
        "variant": "od128-sram", "source_sha256": candidate()["source_sha256"], "pdk": pdk,
        "physical_metrics": review, "metrics_sha256": digest(run / "final/metrics.json"),
        "resolved_config_sha256": digest(run / "resolved.json"), "netlist_sha256": digest(netlist),
        "macro_views": actual_views, "fast_model_boundary": FAST_BOUNDARY,
        "power_connections_sha256": digest(power / "power-connections.json"),
        "buffer_connectivity_audit_sha256": digest(buffer / "connectivity-audit.json"),
        "production": inputs.get("production", "NOT_PROMOTED"),
    }
    if pin_guard:
        result["public_pin_power_audit_sha256"] = digest(pin_guard)
    if "power_port_selection" in inputs:
        selection = one_stage(run, "Project.SelectSramPowerPorts")
        receipt = read(selection / "power-port-audit/selection.json")
        require(receipt["status"] == "PASS_EXISTING_FULL_HEIGHT_POWER_PORT_SELECTION" and
                receipt["removed_internal_rectangles"] == 146 and receipt["remaining_external_rectangles"] == 54 and
                len(receipt["ports"]) == 200, "power-port selection differs")
        before, after = read(selection / "state_in.json"), read(selection / "state_out.json")
        require(receipt["input_odb_sha256"] == digest(Path(before["odb"])), "power-port input database differs")
        for side, state in (("before", before), ("after", after)):
            path = selection / "power-port-audit" / (side + ".def")
            require(digest(path) == receipt[side + "_def_sha256"] == digest(Path(state["def"])),
                    "power-port DEF differs: " + side)
        result["power_port_selection_sha256"] = digest(selection / "power-port-audit/selection.json")
    if "magic_contact_alignment" in inputs:
        drc = one_stage(run, "Magic.DRC")
        directory = drc / "sram-magic-aligned"
        alignment = read(directory / "alignment.json")
        require(alignment["status"] == "STAGED_EXACT_CONTACT_RULE_ALIGNMENT" and
                alignment["original_tree_sha256"] == MAGIC_TREE_SHA256 and
                alignment["references"] == REFERENCE_SHA256 and
                alignment["changed_files"] == ALIGNED_SHA256, "Magic rule alignment differs")
        require(alignment["native_drc_script_sha256"] == digest(directory / "native-drc.tcl") == NATIVE_DRC_SHA256,
                "original complete DRC script differs")
        for key, name in (("helper_sha256", "align_sram_magic.py"), ("startup_sha256", "sram_magicrc.tcl")):
            require(alignment[key] == inputs["staged_sha256"][name], "executed Magic setup differs")
        require({n: digest(directory / n) for n in alignment["staged_files"]} == alignment["staged_files"],
                "actual aligned Magic files changed")
        require({n: h for n, h in alignment["staged_files"].items() if h != alignment["original_files"][n]} == ALIGNED_SHA256,
                "unexpected additional Magic changes")
        result["magic_contact_alignment_sha256"] = digest(directory / "alignment.json")
    write(args.output, result)
    require(review["status"] == "PASS", "physical metrics failed: " + "; ".join(review["errors"]))
    print("PASS: identified SRAM physical metrics; independent precheck and netlist gates remain")


def verify_macro_netlist(path):
    text = Path(path).read_text(encoding="utf-8")
    require("sg13cmos5l_" in text, "not an actual CMOS5L netlist")
    require(len(re.findall(re.escape(MACRO) + r"\s+\\store\.program_memory\s", text)) == 1,
            "expected one real SRAM instance")
    require(not re.search(r"\b(always|initial)\s*(@|begin)", text), "behavioral RTL in physical netlist")


def check_tests(args):
    require(args.require_netlist, "official SRAM gate requires actual submitted netlist")
    physical_g2.check_tests(args)
    verify_macro_netlist(ROOT / "test/gate_level_netlist.v")
    manifest = candidate()
    models = args.staging / "candidate/models"
    require({name: digest(models / name) for name in manifest["model_sha256"]} == manifest["model_sha256"],
            "SRAM simulation models changed")
    result = read(args.output)
    result.update(variant="od128-sram", model_sha256=manifest["model_sha256"],
                  fast_model_boundary=FAST_BOUNDARY, source_sha256=manifest["source_sha256"])
    write(args.output, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for action, function in (("prepare", prepare), ("check-run", check_run), ("check-tests", check_tests)):
        sub = actions.add_parser(action)
        sub.add_argument("--output", type=Path, required=True)
        sub.set_defaults(function=function)
        if action == "prepare":
            sub.add_argument("--stage-ci", action="store_true")
            sub.add_argument("--production", action="store_true", help="Verify actual qualified production before staging; require identical generated files.")
            sub.add_argument("--guarded", action="store_true", help="D45 core-bounded power stripes, vendor SRAM import and mandatory fixed-pin guard.")
            sub.add_argument("--align-magic", action="store_true", help="D46 exact contact-rule alignment and import scheduling; requires --guarded.")
            sub.add_argument("--power-ports", action="store_true", help="D47 existing full-height supply ports only; requires --guarded --align-magic.")
        else:
            sub.add_argument("--staging", type=Path, default=STAGING)
        if action == "check-run":
            sub.add_argument("--run", type=Path, default=ROOT / "runs/wokwi")
        if action == "check-tests":
            sub.add_argument("--junit", type=Path, required=True)
            sub.add_argument("--records", type=Path, required=True)
            sub.add_argument("--require-netlist", action="store_true")
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
