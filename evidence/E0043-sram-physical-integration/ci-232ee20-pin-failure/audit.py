"""Bind original SRAM layout, manufacturing and public netlist CI archives."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from sram_official_frozen_support import load

read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
TOP = 'tt_um_khangelani_protocol_emulator'
MACRO = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
REQUIRED = {'GDS_logs', 'tt_submission', 'sram-physical-candidate',
            'precheck_reports', 'gatelevel_test_results', 'sram-netlist-check'}


def audit(base, out, *, physical_only=False):
    run = read(base / 'run.json')
    producing = load(run['head_sha'], out / 'producer')
    common, physical_g2, physical_sram = producing.common, producing.physical_g2, producing.physical_sram
    require, frozen = common.require, producing.frozen
    Archive = producing.audit.Archive
    require_finished, inspect_precheck, inspect_area = (getattr(producing.audit, name) for name in
        ('require_finished', 'inspect_precheck', 'inspect_area'))
    inspect_runtime, inspect_consumed_artifact = producing.runtime.inspect_runtime, producing.runtime.inspect_consumed_artifact
    require(run['path'] == '.github/workflows/gds-sram.yaml', 'wrong workflow')
    job_list = read(base / 'jobs.json')['jobs']
    if physical_only:
        require(run['status'] in ('in_progress', 'completed'), 'workflow has not started')
        jobs = {job['name']: job for job in job_list}
        require(len(jobs) == len(job_list) and set(jobs) == {'gds', 'precheck', 'gl_test'}, 'unexpected job set')
        require(jobs['gds']['status'] == 'completed' and jobs['gds']['conclusion'] == 'success', 'physical job did not pass')
        require(all(job['run_id'] == run['id'] and job['head_sha'] == run['head_sha'] for job in job_list), 'job identity differs')
    else:
        jobs = require_finished(run, job_list)
    source = run['head_sha']
    required = {'GDS_logs', 'tt_submission', 'sram-physical-candidate'} if physical_only else REQUIRED
    records = [a for a in read(base / 'artifacts.json')['artifacts'] if a['name'] in required]
    require(len(records) == len(required) and {a['name'] for a in records} == required, 'missing or duplicate required archive')
    archives = {a['name']: Archive(base, a, run) for a in records}
    try:
        logs, submission, staged = (archives[n] for n in ('GDS_logs', 'tt_submission', 'sram-physical-candidate'))
        inputs = staged.json('build/sram-physical/inputs.json')
        candidate = json.loads(frozen(source, 'evidence/E0042-sram-prefetch-screen/candidate.json'))
        require(inputs['candidate'] == candidate == physical_sram.candidate(), 'candidate identity drift')
        require(inputs['workflow_source_commit'] == source and inputs['staged_in_ci'], 'staging revision differs')
        require(not inputs['tracked_changes_before_staging'], 'staging checkout was not clean')
        lock = common.candidate_lock()
        require(inputs['flow_lock'] == lock, 'physical lock differs')
        require(inputs['original_config_sha256_lf'] == sha(frozen(source, 'src/config.json')) == lock['config_sha256_lf'], 'base configuration differs')
        require(inputs['metadata_sha256_lf'] == sha(frozen(source, 'info.yaml')), 'metadata differs')
        require(inputs['public_test_names'] == sorted(physical_g2.PUBLIC_TEST_MODULES), 'public selection differs')
        require(inputs['fast_model_boundary'] == physical_sram.FAST_BOUNDARY, 'mixed fast model boundary missing')
        for name, expected in inputs['provenance_sha256'].items():
            require(sha(frozen(source, name)) == expected, 'source revision input differs: ' + name)
            require(sha(staged.bytes('build/sram-physical/inputs/' + name)) == expected, 'retained input differs: ' + name)
        for name, expected in producing.helper_sha256.items():
            require(sha(frozen(source, name)) == expected, 'loaded producing helper changed: ' + name)
        for name, expected in inputs['staged_sha256'].items():
            require(sha(staged.bytes(name)) == expected, 'staged file differs: ' + name)
            if name.startswith('src/'):
                require(sha(logs.bytes(name)) == sha(submission.bytes(name)) == expected, 'built/submitted source differs: ' + name)
        for name, expected in candidate['model_sha256'].items():
            require(sha(staged.bytes('build/sram-physical/candidate/models/' + name)) == expected, 'vendor model differs')
        for name, expected in candidate['source_sha256'].items():
            require(sha(logs.bytes('src/' + name)) == expected, 'actual hardened RTL differs')
        require(inputs.get('guarded_flow') == {
            'core_bounded_stripes': True, 'fixed_public_pin_rectangles': 43,
            'metal4_minimum_spacing_um': 0.42,
            'vendor_import_setup_sha256': physical_sram.SRAM_IMPORT_SETUP_SHA256,
            'vendor_import_patterns': physical_sram.SRAM_IMPORT_PATTERNS,
        }, 'guarded construction contract differs')
        require(inputs.get('magic_contact_alignment') == physical_sram.magic_alignment_contract(), 'Magic alignment contract differs')
        for name in physical_sram.ALIGNED_PLUGIN_FILES:
            require(staged.bytes(name) == frozen(source, 'experiments/i2c/' + name), 'physical helper differs')
        pdk = submission.json('tt_submission/pdk.json')
        require(pdk == logs.json('runs/wokwi/pdk.json'), 'submitted PDK differs')
        require((pdk['FLOW_VERSION'], pdk['PDK'], pdk['PDK_SOURCE'], pdk['PDK_VERSION']) ==
                (lock['librelane'], lock['pdk'], lock['pdk_source'], lock['pdk_commit']), 'actual PDK identity differs')
        resolved = submission.json('tt_submission/resolved.json')
        require(resolved == logs.json('runs/wokwi/resolved.json'), 'submitted physical configuration differs')
        common.verify_run_configuration(resolved, lock)
        require(resolved['meta']['flow'] == 'SramGuardedClassic' and not resolved['meta'].get('substituting_steps'), 'flow changed')
        require(resolved['MAGIC_GDS_FLATGLOB'] == physical_sram.SRAM_IMPORT_PATTERNS, 'vendor SRAM import patterns changed')
        for key in ('RUN_MAGIC_DRC', 'MAGIC_DRC_USE_GDS', 'ERROR_ON_MAGIC_DRC', 'ERROR_ON_ILLEGAL_OVERLAPS',
                    'ERROR_ON_LVS_ERROR', 'ERROR_ON_PDN_VIOLATIONS', 'ERROR_ON_TR_DRC'):
            require(resolved[key] is True, 'acceptance check disabled: ' + key)
        require(resolved['MAX_TRANSITION_CONSTRAINT'] is None and not resolved['RUN_POST_GRT_DESIGN_REPAIR'], 'rejected setting carried over')
        design_dir = PurePosixPath(resolved['DESIGN_DIR'])
        require(design_dir.name == 'src', 'unexpected resolved design directory')
        workspace = design_dir.parent
        require(resolved['MAGICRC'] == str(workspace / 'sram_magicrc.tcl'), 'actual Magic startup differs')
        require(not resolved.get('MAGIC_DRC_MAGLEFS'), 'abstract macro DRC views are forbidden')
        require(resolved['MAGIC_TECH'] == str(PurePosixPath(resolved['PDK_ROOT']) / resolved['PDK'] / 'libs.tech/magic/ihp-sg13cmos5l.tech'), 'original Magic technology path differs')
        require(set(resolved['VERILOG_FILES']) == {str(design_dir / n) for n in candidate['source_sha256']}, 'actual source list differs')
        for key, name in (('PDN_CFG', 'sram_pdn.tcl'), ('SRAM_POWER_MANIFEST', 'sram-preparation.json')):
            require(resolved[key] == str(design_dir / name), 'construction input path differs')
        require(set(resolved['MACROS']) == {MACRO}, 'macro set differs')
        macro = resolved['MACROS'][MACRO]
        require(macro['instances'] == {'store.program_memory': {'location': [20.16, 302.4], 'orientation': 'FS', 'array': None}}, 'macro placement differs')
        require(macro['vh'] == [str(design_dir / (MACRO + '.vh'))], 'macro black box differs')
        require(not macro.get('nl') and not macro.get('spef'), 'unexpected macro override')
        require(inputs['macro_views'] == physical_sram.mapped_macro_views(), 'macro physical identities differ')
        require(set(macro['lib']) == set(physical_sram.MODEL_SETS), 'macro timing set differs')
        for corner, suffix in physical_sram.MODEL_SETS.items():
            require(len(macro['lib'][corner]) == 1 and PurePosixPath(macro['lib'][corner][0]).name == MACRO + '_' + suffix + '.lib', 'macro timing mapping differs')
        for key, folder, extension in (('gds', 'gds', 'gds'), ('lef', 'lef', 'lef'), ('spice', 'cdl', 'cdl')):
            paths = macro[key]
            require(len(paths) == 1 and PurePosixPath(paths[0]).parts[-2:] == (folder, MACRO + '.' + extension), 'macro view differs')
        for path in [p for key in ('gds', 'lef', 'spice') for p in macro[key]] + [p for paths in macro['lib'].values() for p in paths]:
            require('/' + lock['pdk_commit'] + '/ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/' in path, 'macro view points outside pinned PDK')
        stage_configs = {name: logs.json(name) for name in logs.file.namelist()
                         if re.fullmatch(r'runs/wokwi/\d+-[^/]+/config.json', name)}
        def stage(step):
            matches = [name.rsplit('/', 1)[0] for name, config in stage_configs.items() if config.get('meta', {}).get('step') == step]
            require(len(matches) == 1, 'missing/duplicate actual stage: ' + step)
            logs.json(matches[0] + '/state_out.json')
            return matches[0]
        def database(path):
            relative = PurePosixPath(path).relative_to(workspace)
            require(str(relative).startswith('runs/wokwi/'), 'database path escapes producing run')
            return logs.bytes(str(relative))
        power, grid, buffer = (stage(name) for name in ('Project.ConnectSramPower', 'Project.CheckSramPower', 'Project.BufferSramInputs'))
        connection = logs.json(power + '/power-connections.json')
        require(connection['status'] == 'PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING' and len(connection['added_rectangles']) == 144, 'power construction differs')
        require(connection['preparation_sha256'] == inputs['staged_sha256']['src/sram-preparation.json'], 'power manifest changed')
        require(connection['input_odb_sha256'] == sha(database(logs.json(power + '/state_in.json')['odb'])), 'power input database differs')
        grid_metrics = logs.json(grid + '/state_out.json')['metrics']
        for suffix in ('', '__net:VPWR', '__net:VGND'):
            require(grid_metrics['design__power_grid_violation__count' + suffix] == 0, 'fresh power grid not clear')
        buffer_audit = logs.json(buffer + '/connectivity-audit.json')
        require(buffer_audit['status'] == 'PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY' and buffer_audit['added_buffers'] == 9, 'connectivity audit failed')
        for side, state_name in (('before', 'state_in.json'), ('after', 'state_out.json')):
            require(buffer_audit[side + '_odb_sha256'] == sha(database(logs.json(buffer + '/' + state_name)['odb'])), 'connectivity database differs')
        guard = stage('Project.CheckPublicPinPower')
        pin_report = logs.json(guard + '/pin-power-audit/result.json')
        before, after = logs.json(guard + '/state_in.json'), logs.json(guard + '/state_out.json')
        require(pin_report['status'] == 'PASS_PUBLIC_PIN_POWER_GEOMETRY' and not pin_report['violations'] and
                len(pin_report['pins']) == 43 and pin_report['metal4_minimum_spacing_dbu'] == 420, 'public pin geometry failed')
        require(before['odb'] == after['odb'] and pin_report['odb_sha256'] == sha(database(before['odb'])), 'pin guard changed or misidentified database')
        require(logs.bytes(guard + '/pin-power-audit/runner.py') == staged.bytes('audit_sram_pin_power.py'), 'actual pin audit differs')
        for required in ('Magic.DRC', 'Checker.MagicDRC', 'Magic.SpiceExtraction', 'Checker.IllegalOverlap',
                         'Netgen.LVS', 'Checker.LVS', 'Checker.SetupViolations', 'Checker.HoldViolations',
                         'Checker.MaxSlewViolations', 'Checker.MaxCapViolations', 'Misc.ReportManufacturability'):
            stage(required)
        drc_directory = stage('Magic.DRC')
        aligned_directory = drc_directory + '/sram-magic-aligned'
        alignment = logs.json(aligned_directory + '/alignment.json')
        constants = producing.alignment
        require(alignment['status'] == 'STAGED_EXACT_CONTACT_RULE_ALIGNMENT', 'Magic alignment was not staged')
        require(alignment['references'] == constants.REFERENCE_SHA256 and alignment['changed_files'] == constants.ALIGNED_SHA256,
                'Magic rule/reference identities differ')
        original_tree = sha(json.dumps(alignment['original_files'], sort_keys=True, separators=(',', ':')).encode())
        require(original_tree == alignment['original_tree_sha256'] == constants.MAGIC_TREE_SHA256, 'original Magic tree differs')
        require(len(alignment['original_files']) == 35 and set(alignment['staged_files']) == set(alignment['original_files']), 'Magic source membership differs')
        require({n: h for n, h in alignment['staged_files'].items() if h != alignment['original_files'][n]} == constants.ALIGNED_SHA256,
                'unexpected additional rule change')
        for name, expected in alignment['staged_files'].items():
            require(sha(logs.bytes(aligned_directory + '/' + name)) == expected, 'actual copied Magic file differs: ' + name)
        require(alignment['native_drc_script_sha256'] == sha(logs.bytes(aligned_directory + '/native-drc.tcl')) == constants.NATIVE_DRC_SHA256,
                'original complete DRC script differs')
        for key, name in (('helper_sha256', 'align_sram_magic.py'), ('startup_sha256', 'sram_magicrc.tcl')):
            require(alignment[key] == inputs['staged_sha256'][name] == sha(staged.bytes(name)), 'executed Magic helper differs')
        require(resolved['MAGICRC'] in logs.bytes(drc_directory + '/COMMANDS').decode(), 'actual checker did not invoke staged startup')
        report_counts = re.findall(r'\[INFO\] COUNT: (\d+)', logs.bytes(drc_directory + '/reports/drc.magic.rpt').decode())
        require(report_counts == ['0'], 'original complete DRC report is not clear')
        metrics = logs.json('runs/wokwi/final/metrics.json')
        physical = common.inspect_physical_metrics(metrics)
        require(physical['status'] == 'PASS' and metrics['magic__illegal_overlap__count'] == 0, 'physical limits failed')
        require(metrics['design__instance__count__macros'] == 1, 'actual macro missing')
        require(abs(metrics['design__instance__area__macros'] - 49488.4992) < 0.01, 'macro area differs')
        area = inspect_area(submission.bytes('tt_submission/stats/synthesis-stats.txt'), metrics)
        layout = submission.bytes('tt_submission/' + TOP + '.gds')
        netlist = submission.bytes('tt_submission/' + TOP + '.v')
        require(layout == logs.bytes('runs/wokwi/final/gds/' + TOP + '.gds'), 'submitted GDS differs')
        require(layout == database(logs.json(drc_directory + '/state_in.json')['gds']), 'submitted layout differs from actual DRC input')
        require(netlist == logs.bytes('runs/wokwi/final/nl/' + TOP + '.nl.v'), 'submitted netlist differs')
        text = netlist.decode()
        require(len(re.findall(re.escape(MACRO) + r'\s+\\store\.program_memory\s', text)) == 1, 'real SRAM instance missing')
        require(not re.search(r'\b(always|initial)\s*(@|begin)', text), 'behavioral circuit substituted')
        runtime = inspect_runtime((base / 'gds-job.log').read_bytes(), source, lock, jobs['gds']['id'])
        if physical_only:
            return {'status': 'PASS_SRAM_GDS_CHECKS_REMAINING_GATES_PENDING',
                    'physical_qualification': 'NOT_COMPLETE', 'production': 'NOT_PROMOTED',
                    'run_id': run['id'], 'source_commit': source, 'candidate': candidate,
                    'gds_sha256': sha(layout), 'netlist_sha256': sha(netlist),
                    'pdk': pdk, 'physical_metrics': physical, 'area': area, 'runtime': runtime,
                    'magic_contact_alignment': alignment, 'audit_helpers_sha256': producing.helper_sha256,
                    'archives': {name: {'id': a.metadata['id'], 'sha256': a.digest, 'bytes': a.metadata['size_in_bytes']} for name,a in archives.items()},
                    'scope': 'Completed GDS job only; independent precheck and submitted-netlist gates remain required.'}
        consumers = {name: inspect_consumed_artifact((base / (name + '-job.log')).read_bytes(),
                     submission.metadata, lock, jobs[name]['id'], name) for name in ('precheck', 'gl_test')}
        precheck = inspect_precheck(archives['precheck_reports'].bytes('results.xml'))
        net_check = archives['sram-netlist-check']
        checked = net_check.json('test/output/physical-result.json')
        require(checked['status'] == 'PASS' and checked['variant'] == 'od128-sram', 'public netlist checker failed')
        require(checked['evidence_kind'] == 'FUNCTIONAL_ZERO_DELAY_NETLIST' and checked['netlist_sha256'] == sha(netlist), 'tested netlist differs')
        require(checked['source_sha256'] == candidate['source_sha256'] and checked['model_sha256'] == candidate['model_sha256'], 'test source/models differ')
        testing_inputs = net_check.json('build/sram-physical/inputs.json')
        require({k:v for k,v in inputs.items() if k != 'created_utc'} == {k:v for k,v in testing_inputs.items() if k != 'created_utc'}, 'test staging differs')
        tests = archives['gatelevel_test_results']
        junit = out / 'results.xml'
        junit.write_bytes(tests.bytes('results.xml'))
        for name in ('spi/cases.jsonl', 'i2c/cases.jsonl', 'i2c/boundaries.jsonl', 'i2c/aborts.jsonl'):
            path = out / 'records' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(tests.bytes('output/' + name))
        physical_g2.check_tests(SimpleNamespace(junit=junit, records=out / 'records', output=out / 'public-audit.json', require_netlist=False))
        observed = read(out / 'public-audit.json')
        for key in ('public_test_groups', 'excluded_discovered_tests', 'records', 'junit_sha256'):
            require(checked[key] == observed[key], 'public test audit differs: ' + key)
        routed = staged.json('build/sram-physical/resolved-inputs.json')
        require(routed['status'] == 'PASS_PHYSICAL_METRICS_PRECHECK_AND_NETLIST_PENDING', 'routed checker failed')
        require(routed['netlist_sha256'] == sha(netlist) and routed['source_sha256'] == candidate['source_sha256'], 'routed identity differs')
        require(routed['physical_metrics'] == physical and routed['pdk'] == pdk, 'routed result differs')
        for key, name in (('metrics_sha256', 'runs/wokwi/final/metrics.json'), ('resolved_config_sha256', 'runs/wokwi/resolved.json'),
                          ('power_connections_sha256', power + '/power-connections.json'), ('buffer_connectivity_audit_sha256', buffer + '/connectivity-audit.json'),
                          ('public_pin_power_audit_sha256', guard + '/pin-power-audit/result.json')):
            require(routed[key] == sha(logs.bytes(name)), 'routed evidence digest differs: ' + key)
        require(routed['macro_views'] == inputs['macro_views'], 'actually loaded macro views differ')
        require(routed['magic_contact_alignment_sha256'] == sha(logs.bytes(aligned_directory + '/alignment.json')), 'routed alignment receipt differs')
        return {'status': 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES', 'run_id': run['id'], 'source_commit': source,
                'candidate': candidate, 'gds_sha256': sha(layout), 'netlist_sha256': sha(netlist),
                'pdk': pdk, 'physical_metrics': physical, 'area': area, 'runtime': runtime,
                'power_connections': 144, 'native_input_buffers': 9, 'fixed_public_pin_rectangles': 43,
                'public_pin_power_violations': 0, 'vendor_import_patterns': physical_sram.SRAM_IMPORT_PATTERNS,
                'consumer_artifacts': consumers,
                'audit_helpers_sha256': producing.helper_sha256, 'magic_contact_alignment': alignment,
                'precheck': precheck, 'netlist_tests': checked, 'macro_views': inputs['macro_views'],
                'fast_model_boundary': physical_sram.FAST_BOUNDARY,
                'archives': {name: {'id': a.metadata['id'], 'sha256': a.digest, 'bytes': a.metadata['size_in_bytes']} for name,a in archives.items()},
                'scope': 'Exact pinned CMOS5L digital physical flow, official precheck and functional zero-delay public netlist tests. Production adoption/publication remain separate.'}
    finally:
        for archive in archives.values():
            archive.file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--physical-only', action='store_true', help='Audit the completed GDS job without qualifying the candidate')
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True)
    try:
        result = audit(args.directory.resolve(), out, physical_only=args.physical_only)
    except Exception as error:
        (out / 'result.json').write_bytes((json.dumps({'status': 'NOT_QUALIFIED', 'error': str(error)}, indent=2) + '\n').encode())
        raise
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])
