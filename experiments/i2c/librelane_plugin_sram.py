# SPDX-License-Identifier: Apache-2.0
"""Keep the pinned Classic flow and insert the declared SRAM power steps."""
from pathlib import Path

from librelane.config import Variable
from librelane.common import Path as ConfigPath
from librelane.flows import Flow
from librelane.steps import Step
from librelane.steps.odb import OdbpyStep

HERE = Path(__file__).resolve().parent


@Step.factory.register()
class ConnectSramPower(OdbpyStep):
    id = 'Project.ConnectSramPower'
    name = 'Connect SRAM power edges'
    long_name = 'Connect and audit SRAM power edges'
    config_vars = OdbpyStep.config_vars + [
        Variable('SRAM_POWER_MANIFEST', ConfigPath, 'Frozen SRAM power geometry and source manifest.'),
    ]

    def get_script_path(self):
        return str(HERE / 'sram_power_step.py')

    def get_subcommand(self):
        return ['--preparation', str(self.config['SRAM_POWER_MANIFEST']),
                '--report', str(Path(self.step_dir) / 'power-connections.json')]


@Step.factory.register()
class CheckSramPower(Step.factory.get('OpenROAD.GeneratePDN')):
    id = 'Project.CheckSramPower'
    name = 'Check completed SRAM power grid'
    long_name = 'Check both completed power grids without regenerating wires'

    def get_script_path(self):
        return str(HERE / 'check_sram_power.tcl')


Classic = Flow.factory.get('Classic')


@Flow.factory.register()
class SramClassic(Classic):
    Substitutions = [
        ('+Odb.RemovePDNObstructions', ConnectSramPower),
        ('+Project.ConnectSramPower', CheckSramPower),
    ]


assert len(Classic.Steps) == 80
assert [s for s in SramClassic.Steps if not s.id.startswith('Project.')] == Classic.Steps
assert len(SramClassic.Steps) == 82
