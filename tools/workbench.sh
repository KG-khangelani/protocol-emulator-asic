#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="protocol-emulator-asic-workbench:2026-07-29"
command="${1:-All}"
section="${2:-all}"

build_workbench() {
    docker build \
        --file "${repo_root}/tools/workbench/Dockerfile" \
        --tag "${image}" \
        "${repo_root}/tools/workbench"
}

if [[ "${command,,}" == "setup" || "${command,,}" == "build" ]]; then
    build_workbench
    exit 0
fi

if ! docker image inspect "${image}" >/dev/null 2>&1; then
    echo "Workbench image is absent; building ${image}"
    build_workbench
fi

case "${command,,}" in
    doctor) inside=(make doctor) ;;
    check) inside=(make check) ;;
    lint) inside=(make lint) ;;
    test) inside=(make test) ;;
    testverilator|test-verilator) inside=(make test-verilator) ;;
    formal) inside=(make formal) ;;
    synth) inside=(make synth) ;;
    evidence) inside=(make evidence) ;;
    learnstatus|learn-status) inside=(make learn-status) ;;
    learnm0|learn-m0) inside=(python3 tools/m0_walkthrough.py --section "${section,,}") ;;
    learnwaveform|learn-waveform) inside=(make learn-waveform) ;;
    all) inside=(make doctor check lint test test-verilator formal synth) ;;
    shell) inside=(bash) ;;
    *) echo "Usage: $0 {Setup|Build|Doctor|Check|Lint|Test|TestVerilator|Formal|Synth|Evidence|LearnStatus|LearnM0|LearnWaveform|All|Shell} [section]" >&2; exit 2 ;;
esac

exec docker run --rm --init \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --mount "type=bind,source=${repo_root},target=/workspace" \
    --workdir /workspace \
    "${image}" "${inside[@]}"
