/* SPDX-License-Identifier: Apache-2.0 */
// Deterministic source/evidence export, not a hardware execution path.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const repoRoot = fileURLToPath(new URL('../', import.meta.url));
const repository = 'https://github.com/KG-khangelani/protocol-emulator-asic';
const mainSnapshot = '155e130ea402f78a86558fb3c2b094c536be41a4';
const sha = (text) => createHash('sha256').update(text).digest('hex');
const canonical = (text) => text.replaceAll('\r\n', '\n');
const stripComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');

function reader(root, overrides) {
  return (path, required = true) => {
    try {
      if (Object.hasOwn(overrides, path)) {
        if (overrides[path] === null) throw new Error('missing fixture');
        return canonical(overrides[path]);
      }
      return canonical(readFileSync(resolve(root, path), 'utf8'));
    } catch (error) {
      if (required) throw new Error(`Cannot inspect ${path}: ${error.message}`);
      return null;
    }
  };
}

export function sequentialRegisters(source) {
  const text = stripComments(source);
  const declarations = new Map();
  const expression = /\b(?:output\s+)?reg\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([A-Za-z_]\w*(?:\s*,\s*(?!input\b|output\b|wire\b|reg\b)[A-Za-z_]\w*)*)/g;
  for (const match of text.matchAll(expression)) {
    const bits = match[1] === undefined ? 1 : Math.abs(Number(match[1]) - Number(match[2])) + 1;
    for (const name of match[3].split(',').map((part) => part.trim())) declarations.set(name, bits);
  }
  const clocked = [...new Set([...text.matchAll(/\b([A-Za-z_]\w*)\s*<=/g)].map((match) => match[1]))];
  return clocked.map((name) => {
    if (!declarations.has(name)) throw new Error(`Unsupported sequential declaration: ${name}`);
    return { name, bits: declarations.get(name) };
  }).sort((a, b) => a.name.localeCompare(b.name, 'en'));
}

function fields(registers, groups) {
  const used = new Set();
  const rows = groups.map(([label, names]) => {
    const bits = names.reduce((total, name) => {
      const register = registers.find((item) => item.name === name);
      if (!register) throw new Error(`Missing state field ${name}`);
      used.add(name);
      return total + register.bits;
    }, 0);
    return { label, bits, registers: names };
  });
  const extra = registers.filter((item) => !used.has(item.name));
  if (extra.length) rows.push({ label: 'Additional declared state', bits: extra.reduce((n, item) => n + item.bits, 0), registers: extra.map((item) => item.name) });
  return rows;
}

function connections(top, module) {
  const match = stripComments(top).match(new RegExp(`\\b${module}\\s+\\w+\\s*\\(([\\s\\S]*?)\\);`));
  if (!match) throw new Error(`Missing instance ${module}`);
  return Object.fromEntries([...match[1].matchAll(/\.(\w+)\(\s*([A-Za-z_]\w*)\s*\)/g)].map((item) => [item[1], item[2]]));
}

function json(text) { try { return text === null ? null : JSON.parse(text); } catch { return null; } }

export function buildAtlas(root = repoRoot, overrides = {}) {
  const read = reader(root, overrides);
  const definitions = [
    ['top', 'Top-level routing', 'tt_um_khangelani_protocol_emulator', 'src/project.v', 'Public pins, loader ownership and runtime readback', []],
    ['program', 'Program store', 'm1_program_store', 'src/m1_program_store.v', 'Writable through clock-synchronous public pins', [
      ['Program words', Array.from({ length: 8 }, (_, i) => `word${i}`)], ['Length', ['program_length']], ['Ready', ['program_ready']],
    ]],
    ['engine', 'Sequencer', 'm1_engine', 'src/m1_engine.v', 'Accepted-edge temporal execution', [
      ['PC + state', ['pc', 'state']], ['WAIT counter', ['wait_left']],
      ['Input-wait configuration', ['wait_is_input', 'wait_pin', 'wait_level', 'wait_timeout_skip']],
      ['Bounded LOOP', ['loop_active', 'loop_start', 'loop_end', 'loop_remaining']],
      ['SHIFT state', ['shift_active', 'shift_bits_done', 'shift_msb_first', 'shift_tx_pin', 'shift_rx_pin', 'shift_tx_data', 'shift_rx_data', 'shift_period', 'shift_tx_slot']],
      ['GPIO value + direction', ['gpio_value', 'gpio_oe']],
    ]],
    ['data', 'Data registers', 'm1_data_store', 'src/m1_data_store.v', 'Raw capture is not accepted-frame delivery', [
      ['TX A', ['tx_payload']], ['TX B', ['tx_payload_alt']], ['Raw RX', ['rx_result']], ['Raw valid', ['rx_valid']],
    ]],
    ['sync', 'Input synchronizer', 'm1_input_sync', 'src/m1_input_sync.v', 'Always clocked; enable freezes only the engine', [
      ['Stage 1', ['metastability_stage']], ['Stage 2', ['sampled_in']],
    ]],
  ];
  const sourceText = Object.fromEntries(definitions.map((item) => [item[0], read(item[3])]));
  const qualificationText = read('evidence/E0018-uart-rx-public/qualification.json', false);
  const qualification = json(qualificationText);
  const manifestText = read('evidence/E0018-uart-rx-public/ci-manifest.json', false);
  const manifest = json(manifestText);
  const requiredStages = ['doctor', 'static', 'learning_status', 'lint', 'rtl_icarus', 'gl_harness_smoke', 'waveform_provenance', 'learning_waveform', 'rtl_verilator', 'formal', 'generic_synthesis'];
  const recordedCI = (qualified) => qualified?.implementation_ci === 'PASS' ||
    (qualified?.implementation_ci === undefined && ['push_test', 'pull_request_test', 'push_docs'].every((name) => qualified?.runs?.[name]?.conclusion === 'success'));
  const qualifies = (qualified, collected, text) => Boolean(qualified && collected &&
    sha(text) === qualified.clean_collector?.manifest_sha256 &&
    recordedCI(qualified) && qualified.clean_collector?.simulator_failures === 0 &&
    qualified.clean_collector?.stages_passed === requiredStages.length && collected.git_head === qualified.implementation_head &&
    Array.isArray(collected.stages) && collected.stages.length === requiredStages.length &&
    requiredStages.every((name) => collected.stages.some((stage) => stage.name === name && stage.status === 'PASS' && stage.returncode === 0)));
  const evidenceIntegrity = qualifies(qualification, manifest, manifestText);
  const modules = definitions.map(([id, label, name, file, note, groups]) => {
    const registers = sequentialRegisters(sourceText[id]);
    const sourceHash = sha(sourceText[id]);
    return { id, label, name, file, note,
      stateBits: registers.reduce((sum, register) => sum + register.bits, 0),
      registers, fields: groups.length ? fields(registers, groups) : [], sourceHash,
      evidenceSourceMatches: evidenceIntegrity && manifest.source_sha256?.[file] === sourceHash,
      sourceUrl: `${repository}/blob/${qualification?.implementation_head ?? mainSnapshot}/${file}`,
    };
  });
  const allSourceMatches = modules.every((module) => module.evidenceSourceMatches);
  const ports = Object.fromEntries(definitions.filter((item) => item[0] !== 'top').map((item) => [item[0], connections(sourceText.top, item[2])]));
  const relationDefinitions = [
    ['raw-sync', 'top', 'sync', 'uio_in', 'async_in', 'Raw public input', ['uio_in[7:0]'], 'Runtime input directly enters the synchronizer; these pins are shared with the loader.'],
    ['sync-engine', 'sync', 'engine', 'sampled_in', 'sampled_inputs', 'Synchronized input', ['sampled_inputs[7:0]'], 'Synchronized level used by input waits and receive sampling.'],
    ['program-engine', 'program', 'engine', 'instruction', 'instruction', 'Instruction fetch', ['instruction[31:0]', 'instruction_valid'], 'Program data, not a read-only preload.'],
    ['engine-program', 'engine', 'program', 'pc', 'pc', 'Fetch address', ['pc[4:0]'], 'No implicit address wrap.'],
    ['data-engine', 'data', 'engine', 'tx_payload', 'tx_payload', 'Transmit payload', ['tx_payload[7:0]', 'tx_payload_alt[7:0]'], 'Two generic public payload registers.'],
    ['engine-data', 'engine', 'data', 'shift_result_data', 'shift_result_data', 'Raw result capture', ['shift_result_data[7:0]', 'shift_result_write'], 'Result and write strobe; capture does not imply frame acceptance.'],
    ['engine-output', 'engine', 'top', 'gpio_value', 'gpio_value', 'Runtime GPIO', ['gpio_value[7:0]', 'gpio_oe[7:0]'], 'Runtime uio_out/uio_oe; uo_out is status or selected register readback.'],
  ];
  const relations = relationDefinitions.map(([id, from, to, sourcePort, targetPort, label, signals, note]) => {
    const sourceWire = from === 'top' ? sourcePort : ports[from]?.[sourcePort];
    const targetWire = to === 'top' ? targetPort : ports[to]?.[targetPort];
    if (!sourceWire || sourceWire !== targetWire) throw new Error(`Source wiring mismatch for ${id}`);
    return { id, from, to, sourcePort, targetPort, wire: sourceWire, label, signals, note };
  });
  // Every additional named signal must also connect to the same source/destination.
  for (const [from, to, port] of [['program', 'engine', 'instruction_valid'], ['data', 'engine', 'tx_payload_alt'], ['engine', 'data', 'shift_result_write']]) {
    if (ports[from]?.[port] !== ports[to]?.[port]) throw new Error(`Source wiring mismatch for ${port}`);
  }
  if (!/engine_rst_n\s*=\s*rst_n\s*&&\s*program_ready\s*&&\s*!load_mode/.test(sourceText.top)) throw new Error('Unrecognized engine reset predicate');
  if (!/uio_out\s*=\s*load_mode\s*\?\s*loader_data_out\s*:\s*gpio_value/.test(sourceText.top)) throw new Error('Unrecognized runtime GPIO ownership');
  const learning = json(read('docs/learning/progress.json'));
  const ownerM0 = learning?.milestones?.find((item) => item.id === 'M0');
  const ledger = read('docs/research-ledger.md');
  const hypotheses = ['H1', 'H2', 'H3', 'H4'].map((id) => {
    const row = ledger.split('\n').find((line) => line.startsWith(`| ${id} |`));
    const status = row?.split('|').at(-2)?.trim().toUpperCase();
    return { id, status: status || 'NOT_VERIFIED' };
  });
  const physical = json(read('evidence/E0010-pinned-cmos5l-run/result.json', false));
  const physicalPass = ['gds', 'precheck', 'gate_level'].every((job) => physical?.jobs?.[job]?.status === 'PASS');
  const tx = json(read('evidence/E0016-uart-tx-8n1/qualification.json', false));
  const txManifestText = read('evidence/E0016-uart-tx-8n1/ci-manifest.json', false);
  const txManifest = json(txManifestText);
  const txPass = qualifies(tx, txManifest, txManifestText);
  const tools = (manifest) => Object.entries(manifest?.tools ?? {}).map(([name, version]) => ({ name, version: String(version).replace(/\s+/g, ' ') }));
  const physicalTools = ['flow', 'flow_version', 'pdk', 'pdk_commit', 'physical_yosys', 'gate_level_iverilog', 'gate_level_cocotb'].map((name) => ({ name, version: physical?.resolved_environment?.[name] ?? 'Unavailable' }));
  const record = (id, title, revision, status, rung, scope, path, extra = {}) => ({
    id, title, revision, status, rung, scope, evidenceUrl: `${repository}/blob/${mainSnapshot}/${path}`, ...extra,
  });
  const evidence = [
    record('E0010', 'Archived M0 GPIO baseline', physical?.source_commit ?? '', physicalPass ? 'PASS' : 'NOT_VERIFIED', 'CMOS5L + gate-level + clean rerun',
      'Archived GPIO counter only. This does not qualify current M1 hardware or owner learning.', 'evidence/E0010-pinned-cmos5l-run/README.md', { archived: true, runUrl: physical?.run_url ?? '', tools: physicalTools }),
    record('E0016', 'UART TX 8N1', tx?.implementation_head ?? '', txPass ? 'PASS' : 'NOT_VERIFIED', 'Recorded digital RTL / scoped formal',
      'Named firmware workload, not complete UART or current M1 physical evidence.', 'evidence/E0016-uart-tx-8n1/README.md', { archived: false, currentSourceMatches: false, tools: tools(txManifest) }),
    record('E0018', 'Bounded last-byte UART RX', qualification?.implementation_head ?? '', evidenceIntegrity ? 'PASS' : 'NOT_VERIFIED', 'Digital RTL / scoped formal',
      'Both frames validate; only final byte delivered after known-image HALT. Raw valid is capture, not acceptance. No FIFO/continuous receive.', 'evidence/E0018-uart-rx-public/README.md',
      { archived: false, currentSourceMatches: allSourceMatches, manifestIntegrity: evidenceIntegrity, tools: tools(manifest), runUrl: `${repository}/actions/runs/${qualification?.runs?.push_test?.id ?? ''}` }),
  ];
  const metadata = read('info.yaml');
  return {
    schema: 'protocol-atlas-source-v1', repository,
    source: { revision: qualification?.implementation_head ?? mainSnapshot, mainSnapshot, allSourceMatches, evidenceIntegrity,
      fingerprint: sha(modules.map((module) => `${module.file}:${module.sourceHash}`).join('\n')), qualification: 'E0018', matchCount: modules.filter((module) => module.evidenceSourceMatches).length },
    clockTargetHz: Number(metadata.match(/clock_hz:\s*(\d+)/)?.[1] ?? 0),
    tileAllocation: metadata.match(/tiles:\s*["']?([0-9]+x[0-9]+)/)?.[1] ?? 'Unknown',
    modules, relations, totalStateBits: modules.reduce((sum, module) => sum + module.stateBits, 0),
    evidence,
    genericScreen: { cells: qualification?.clean_collector?.generic_cells ?? null, stateBits: qualification?.clean_collector?.state_bits ?? null, qualification: 'E0018', provenance: 'MEASURED', scope: 'Generic synthesis only; not CMOS5L area/fit/timing.' },
    learning: { activeMilestone: learning?.active_milestone ?? 'Unknown', m0Technical: ownerM0?.technical_gate?.status ?? 'Unknown', m0Fluency: ownerM0?.fluency_gate?.status ?? 'Unknown' },
    hypotheses,
    deferred: { id: 'PR8', branch: 'feat/bounded-uart-rx-host-service', head: 'b19a718e25b2f6e3343a15a1632aaed7da14c05f', snapshotDate: '2026-10-05', status: 'DRAFT / NOT MERGED', url: `${repository}/pull/8`, scope: 'Separate host-service branch. Its cache is external to CHIP_COMPLETE; evidence is not imported in this app snapshot.' },
    limits: ['Logical geometry is schematic, not physical area.', 'Reference playback is not measured RTL or a hardware capture.', '50 MHz is a target, not measured Fmax.', 'M1 physical closure and silicon: NOT EVALUATED.', 'M0 owner fluency is not promoted by engineering.'],
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const target = resolve(repoRoot, 'web/src/data/atlas.json');
  const output = JSON.stringify(buildAtlas(), null, 2) + '\n';
  if (process.argv.includes('--check')) {
    if (readFileSync(target, 'utf8') !== output) throw new Error('Atlas data differs from current sources/evidence; run npm run data and inspect the delta.');
    console.log('PASS: source graph, sequential-state accounting and curated evidence dataset match');
  } else {
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, output);
    console.log('Wrote deterministic public source/evidence data; no private assets or hardware execution');
  }
}
