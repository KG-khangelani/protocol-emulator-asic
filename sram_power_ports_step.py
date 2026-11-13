# SPDX-License-Identifier: Apache-2.0
"""Use the native ODB reader/writer for the audited supply-port selection."""
import hashlib
import json
from pathlib import Path

import click
from reader import click_odb

from select_sram_power_ports import select_ports


@click.command()
@click.option('--audit-directory', type=click.Path(path_type=Path), required=True)
@click_odb
def main(reader, audit_directory, input_db):
    result = select_ports(reader.db, audit_directory)
    result['input_odb_sha256'] = hashlib.sha256(Path(input_db).read_bytes()).hexdigest()
    (audit_directory / 'selection.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
