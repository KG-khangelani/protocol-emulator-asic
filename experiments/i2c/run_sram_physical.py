# SPDX-License-Identifier: Apache-2.0
"""Bound an identified integrated SRAM pilot or complete pinned flow."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from sram_prefetch import ROOT, digest

sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from run_program_sensitivity import execute


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--full', action='store_true')
    args = p.parse_args()
    base = args.directory.resolve()
    preparation = json.loads((base / 'preparation.json').read_bytes())
    assert preparation['status'] == 'PREPARED_UNQUALIFIED_INTEGRATED_PDN_TRIAL'
    assert base.is_relative_to((ROOT / 'build').resolve()) and not (base / 'run-result.json').exists()
    for name, sha in preparation['plugin_sha256'].items():
        assert digest((base / name).read_bytes()) == sha
    for name, sha in preparation['source_sha256'].items():
        assert digest((base / 'src' / name).read_bytes()) == sha
    assert digest((base / 'src/config_merged.json').read_bytes()) == preparation['config_sha256']
    (base / 'inputs' / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    result = {'status': 'RUNNING', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'mode': 'full' if args.full else 'power-pilot', 'physical_qualification': 'NOT_EVALUATED'}
    save = lambda: (base / 'run-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    save()
    env = dict(os.environ, PYTHONPATH=str(base))
    command = ['librelane', '--pdk-root', '/pdk', '--pdk', 'ihp-sg13cmos5l',
               '--run-tag', 'integrated', '--design-dir', str(base)]
    if not args.full:
        command += ['--to', 'Project.CheckSramPower']
    command.append(str(base / 'src/config_merged.json'))
    try:
        result['execution'] = execute(command, base / 'run.log', 10800 if args.full else 300, env=env)
        assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
        result['status'] = 'COMMAND_SUCCEEDED_REQUIRES_ARTIFACT_AUDIT'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'])


if __name__ == '__main__':
    main()
