# SPDX-License-Identifier: Apache-2.0
"""Compare the archived FabricFox runs and optionally check a new run against them."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE_SHA256 = '89fa89607e0eac4468d11257b4b46296f9122115e0995c888274d31387fb4163'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(reference, candidate):
    # A later documentation-only commit can reproduce the same inputs and image.
    identities = {'started_utc', 'ended_utc', 'source_commit'}
    require(set(reference) == set(candidate), 'result fields differ')
    for key in sorted(set(reference) - identities):
        require(candidate[key] == reference[key], 'run differs in ' + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, help='also verify the artifacts in this new run directory')
    args = parser.parse_args()
    reference = json.loads((HERE / 'result.json').read_bytes())
    first = json.loads((HERE / 'first-result.json').read_bytes())
    require(reference['status'] == 'PASS_FPGA_REHEARSAL', 'reference rehearsal failed')
    require(first['source_commit'] == reference['source_commit'], 'archived source commits differ')
    compare(reference, first)
    image = (HERE / 'fabricfox-v2-12p5mhz.bin').read_bytes()
    require(sha(image) == reference['bitstream_sha256'] == IMAGE_SHA256, 'archived configuration hash differs')
    require(len(image) == reference['bitstream_bytes'], 'archived configuration length differs')
    for route in reference['routes']:
        name = 'timing-' + str(route['target_mhz']) + '.json.gz'
        timing = gzip.decompress((HERE / name).read_bytes())
        require(sha(timing) == route['timing_sha256'], 'archived report differs: ' + name)
    if args.run:
        run = args.run.resolve()
        candidate = json.loads((run / 'result.json').read_bytes())
        compare(reference, candidate)
        selected = 'route-' + str(candidate['selected_mhz'])
        require((run / selected / 'fabricfox.bin').read_bytes() == image, 'fresh configuration bytes differ')
        require(sha((run / 'decoded.v').read_bytes()) == reference['decoded_sha256'], 'fresh decoded logic differs')
        require(json.loads((run / 'observations.json').read_bytes()) == reference['pins'], 'fresh pin record differs')
        for route in reference['routes']:
            report = run / ('route-' + str(route['target_mhz'])) / 'timing.json'
            require(sha(report.read_bytes()) == route['timing_sha256'], 'fresh routing report differs: ' + str(report))
    print('PASS_FPGA_REPRODUCTION', IMAGE_SHA256)


if __name__ == '__main__':
    main()
