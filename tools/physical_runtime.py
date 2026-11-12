# SPDX-License-Identifier: Apache-2.0
"""Verify runtime identities from completed official GDS job logs."""
import hashlib
import re

def inspect_runtime(raw: bytes, source: str, lock: dict, job_id: int) -> dict:
    text = raw.decode("utf-8")
    actions = dict(re.findall(r"Download action repository '([^']+)' \(SHA:([0-9a-f]{40})\)", text))
    outer = lock["outer_action_repository"] + "@" + lock["outer_action_commit"]
    checkout = "actions/checkout@" + lock["checkout_action_commit"]
    assert actions.get(outer) == lock["outer_action_commit"], "actual outer action mismatch"
    assert actions.get(checkout) == lock["checkout_action_commit"], "actual checkout action mismatch"
    for label, commit in [("source", source), ("support", lock["support_tools_commit"])]:
        assert re.search(r"^\S+Z " + re.escape(commit) + r"\s*$", text, re.M), f"missing actual {label} checkout"
    image = lock["librelane_image"]
    digest = image.split("@", 1)[1]
    assert re.search(r"^\S+Z Digest: " + re.escape(digest) + r"\s*$", text, re.M), "missing immutable image pull digest"
    assert re.search(r"^\S+Z Status: (Downloaded newer image for|Image is up to date for) " + re.escape(image) + r"\s*$", text, re.M), "missing successful image pull"
    versions = sorted(set(re.findall(r"Yosys ([0-9.]+) \(git sha1 ([0-9a-f]{40})", text)))
    assert len(versions) == 1, ("missing or inconsistent physical Yosys version", versions)
    lines = [line.rstrip() for line in text.splitlines()
             if ("Digest: " + digest) in line or ("Status: " in line and image in line) or
             ("Yosys " + versions[0][0] + " (git sha1 " + versions[0][1]) in line]
    return {
        "status": "PASS_RUNTIME_IDENTITIES",
        "job_id": job_id,
        "log_sha256": hashlib.sha256(raw).hexdigest(),
        "workflow_source_commit": source,
        "support_tools_commit": lock["support_tools_commit"],
        "librelane_image_pull_verified": image,
        "physical_yosys": {"version": versions[0][0], "commit": versions[0][1]},
        "resolved_actions": actions,
        "confirmation_lines": lines,
        "scope": "Completed GDS log observations. Tagged transitive actions are observed identities, not new repository pins; PDK/resolved configuration and artifact checks are separate."
    }

def inspect_consumed_artifact(raw: bytes, artifact: dict, lock: dict, job_id: int, kind: str) -> dict:
    text=raw.decode("utf-8")
    assert kind in {"precheck","gl_test"} and artifact["name"]=="tt_submission"
    expected=f'- tt_submission (ID: {artifact["id"]}, Size: {artifact["size_in_bytes"]}, Expected Digest: {artifact["digest"]})'
    digest=artifact["digest"].split(":",1)[1]
    assert expected in text,"consumer did not identify the expected submission archive"
    assert f"SHA256 digest of downloaded artifact is {digest}" in text,"downloaded submission digest mismatch"
    assert "Artifact download completed successfully." in text,"submission download did not complete"
    actions=dict(re.findall(r"Download action repository '([^']+)' \(SHA:([0-9a-f]{40})\)",text))
    assert actions.get(lock["outer_action_repository"]+"@"+lock["outer_action_commit"])==lock["outer_action_commit"],"consumer outer action mismatch"
    cache_key=f'Linux-pdk-{lock["pdk"]}-{lock["pdk_commit"]}'
    enabled=f'Version {lock["pdk_commit"]} enabled for the ihp-sg13 PDK.' in text
    restored=f'Cache restored from key: {cache_key}' in text and 'Cache restored successfully' in text
    assert enabled or restored,"consumer PDK activation or exact cache restore not verified"
    source=artifact["workflow_run"]["head_sha"]
    if kind=="precheck":
        assert re.search(r"^\S+Z "+re.escape(lock["support_tools_commit"])+r"\s*$",text,re.M),"precheck support checkout mismatch"
        assert "Precheck passed for " in text and "/tt_submission/tt_um_khangelani_protocol_emulator.gds" in text,"passing precheck target not verified"
    else:
        assert re.search(r"^\S+Z "+re.escape(source)+r"\s*$",text,re.M),"netlist-test source checkout mismatch"
        compile_lines=[line for line in text.splitlines() if '/usr/bin/iverilog -o ' in line]
        assert len(compile_lines)==1 and all(token in compile_lines[0] for token in ['-DGL_TEST','/test/gate_level_netlist.v','/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v']),"actual physical netlist/model compiler inputs missing"
    return {"status":"PASS_CONSUMED_EXACT_SUBMISSION","job_id":job_id,"kind":kind,
            "log_sha256":hashlib.sha256(raw).hexdigest(),"submission_artifact_id":artifact["id"],
            "submission_archive_sha256":digest,"workflow_source_commit":source if kind=="gl_test" else None,
            "support_tools_commit":lock["support_tools_commit"] if kind=="precheck" else None,
            "support_tools_scope":"checked out" if kind=="precheck" else "not used by the official GL action",
            "resolved_actions":actions,"pdk_activation_verified":lock["pdk_commit"],
            "pdk_activation_method":"ciel_enable" if enabled else "exact_pdk_cache_restore",
            "simulation_versions_observed":[line.rstrip() for line in text.splitlines() if 'Running on Icarus Verilog version ' in line or 'Initialized cocotb v' in line],
            "confirmation_lines":[l.rstrip() for l in text.splitlines() if expected in l or
                                  f"SHA256 digest of downloaded artifact is {digest}" in l or
                                  "Precheck passed for " in l or
                                  f'Cache restored from key: {cache_key}' in l or
                                  f'Version {lock["pdk_commit"]} enabled for the ihp-sg13 PDK.' in l]}
