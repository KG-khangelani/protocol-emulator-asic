"""Load only audit definitions and reference data from the producing Git revision."""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def load(source, destination):
    assert re.fullmatch('[0-9a-f]{40}', source)
    destination = Path(destination).resolve()
    assert destination.is_relative_to(ROOT / 'build') and not destination.exists()
    destination.mkdir(parents=True)
    loaded = {}
    def frozen(commit, name):
        assert commit == source
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        path = destination / name
        if not path.exists():
            index = json.loads((HERE / 'producer.json').read_bytes())
            assert source == index['source_commit']
            archive = HERE / 'producer.tar.gz'
            assert hashlib.sha256(archive.read_bytes()).hexdigest() == index['sha256']
            with tarfile.open(archive) as stream:
                raw = stream.extractfile(name).read()
            assert hashlib.sha256(raw).hexdigest() == index['files'][name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return path.read_bytes()
    def selected(name, names, scope):
        raw = frozen(source, name)
        nodes = []
        for node in ast.parse(raw).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
                nodes.append(node)
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
                nodes.append(node)
        assert len(nodes) == len(names), (name, names, len(nodes))
        exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), scope)
        loaded[name] = hashlib.sha256(raw).hexdigest()
        return SimpleNamespace(**{name: scope[name] for name in names})
    common = selected('tools/physical_candidate.py', [
        'require', 'digest', 'read_json', 'write_json', 'candidate_lock', 'verify_run_configuration',
        'inspect_physical_metrics', 'SIGNOFF_CORNERS', 'PUBLIC_TESTS', 'PUBLIC_TEST_MODULES', 'EXCLUDED_TESTS'],
        dict(Path=Path, hashlib=hashlib, json=json, math=math, ROOT=destination))
    frozen(source, 'tools/workbench/toolchain.lock.json')
    physical_g2 = selected('tools/physical_g2.py', ['PUBLIC_TEST_MODULES', 'records', 'check_public_records', 'check_tests'],
        dict(common=common, ET=ET, gzip=gzip, json=json, ROOT=destination,
             EVIDENCE=destination / 'evidence/E0036-g2-store-and-ci', require=common.require,
             digest=common.digest, write_json=common.write_json))
    for name in ('architecture/combined/icarus/records/cases.jsonl.gz',
                 'od128/protocols/icarus/records/cases.jsonl.gz',
                 'architecture/boundaries/od128-icarus/records/boundaries.jsonl.gz',
                 'architecture/aborts/od128-icarus/records/aborts.jsonl.gz'):
        frozen(source, 'evidence/E0036-g2-store-and-ci/ci/' + name)
    alignment = selected('experiments/i2c/align_sram_magic.py',
        ['REFERENCE_SHA256', 'ALIGNED_SHA256', 'MAGIC_TREE_SHA256', 'NATIVE_DRC_SHA256'], {})
    sram_scope = dict(vars(alignment), json=json, tarfile=tarfile, require=common.require,
        digest=common.digest, read=common.read_json, sha=lambda raw: hashlib.sha256(raw).hexdigest(),
        EVIDENCE=destination / 'evidence/E0042-sram-prefetch-screen')
    physical_sram = selected('tools/physical_sram.py', ['PLUGIN_FILES', 'GUARDED_PLUGIN_FILES', 'ALIGNED_PLUGIN_FILES',
        'SRAM_IMPORT_PATTERNS', 'SRAM_IMPORT_SETUP_SHA256', 'MODEL_SETS', 'FAST_BOUNDARY',
        'candidate', 'mapped_macro_views', 'magic_alignment_contract'], sram_scope)
    physical_sram.MACRO = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
    for name in ('candidate.json', 'mapped/archive.json', 'mapped/mapping.tar.gz'):
        frozen(source, 'evidence/E0042-sram-prefetch-screen/' + name)
    audit = selected('tools/audit_g2_physical.py', ['Archive', 'require_finished', 'inspect_precheck', 'inspect_area', 'PRECHECK_NAMES'],
        dict(common=common, require=common.require, json=json, zipfile=zipfile, ET=ET, re=re, math=math,
             sha=lambda raw: hashlib.sha256(raw).hexdigest()))
    runtime = selected('tools/physical_runtime.py', ['inspect_runtime', 'inspect_consumed_artifact'],
        dict(hashlib=hashlib, re=re))
    return SimpleNamespace(common=common, physical_g2=physical_g2, physical_sram=physical_sram,
        alignment=alignment, audit=audit, runtime=runtime, frozen=frozen,
        helper_sha256=loaded, directory=destination)
