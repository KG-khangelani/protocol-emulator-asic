# SPDX-License-Identifier: Apache-2.0
"""LibreLane's native ODB reader/writer around the verified edge connector."""
import hashlib
import json
from pathlib import Path

import click
from reader import click_odb

from connect_sram_power import connect


@click.command()
@click.option('--preparation', type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--report', type=click.Path(path_type=Path), required=True)
@click_odb
def main(reader, preparation, report, input_db):
    result = connect(reader.db, json.loads(preparation.read_bytes()))
    result.update(input_odb_sha256=hashlib.sha256(Path(input_db).read_bytes()).hexdigest(),
                  preparation_sha256=hashlib.sha256(preparation.read_bytes()).hexdigest())
    report.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
