/* SPDX-License-Identifier: Apache-2.0 */
// Read an existing qualification; the atlas never runs or grants qualification.
import { createHash } from 'node:crypto';
const sha = (text) => createHash('sha256').update(text).digest('hex');
const parse = (text) => { try { return JSON.parse(text); } catch { return null; } };
const sameMap = (left, right) => left && right && Object.keys(left).length === Object.keys(right).length &&
  Object.entries(left).every(([key, value]) => right[key] === value);

export function productionRecord(read) {
  const raw = read('tools/production-profile.json', false);
  if (raw === null) return null;
  const profile = parse(raw);
  const reference = (entry) => {
    if (!entry || typeof entry.path !== 'string' || !entry.path.startsWith('evidence/') || entry.path.includes('..')) return null;
    const text = read(entry.path, false);
    return text !== null && sha(text) === entry.sha256 ? parse(text) : null;
  };
  const physical = reference(profile?.qualification);
  const combined = reference(profile?.combined_regression);
  const normal = reference(profile?.normal_command_verification);
  const pair = reference(profile?.corrected_netlist_pair);
  const candidate = physical?.candidate;
  const files = profile?.files_sha256;
  const actualFilesMatch = files && Object.keys(files).length === 20 && Object.entries(files).every(([path, digest]) => {
    if (path.includes('..') || path.startsWith('/') || path.includes('\\')) return false;
    const text = read(path, false);
    return text !== null && sha(text) === digest;
  });
  const qualified = Boolean(profile?.schema === 'protocol-emulator-production-profile-v1' && profile.profile === 'od128-sram' &&
    physical?.status === 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES' && physical.physical_metrics?.status === 'PASS' &&
    Object.keys(physical.jobs ?? {}).length === 3 && ['gds', 'precheck', 'gl_test'].every((name) => physical.jobs?.[name]?.conclusion === 'success') &&
    ['source_commit', 'run_id', 'gds_sha256', 'netlist_sha256'].every((name) => physical[name] === profile.qualification[name]) &&
    sameMap(files, physical.staged_sha256) && actualFilesMatch && sha(read('info.yaml')) === profile.metadata_sha256 &&
    combined?.status === 'PASS_SRAM_CURRENT_BOTH_SIMULATORS' && sameMap(combined.candidate?.source_sha256, candidate?.source_sha256) &&
    normal?.status === 'PASS_CURRENT_SRAM_COMMAND_CI_ORIGINAL_ARCHIVE' && sameMap(normal.profile?.source_sha256, candidate?.source_sha256) &&
    sameMap(normal.profile?.model_sha256, candidate?.model_sha256) && sameMap(profile.model_sha256, candidate?.model_sha256) &&
    pair?.status === 'PASS_RETAINED_CORRECTED_NETLIST_PAIR_WITH_FROZEN_INPUTS' && pair.netlist_sha256 === physical.netlist_sha256 &&
    physical.netlist_tests?.status === 'PASS' && physical.netlist_tests.public_test_groups === 18);
  const version = /^v\d+\.\d+\.\d+-[\w.-]+$/.test(profile?.release_tag ?? '') ? profile.release_tag : 'main';
  return { qualified, version, sourceHashes: candidate?.source_sha256 ?? {},
    physicalSource: physical?.source_commit ?? '', runId: physical?.run_id ?? null,
    logicalWords: candidate?.logical_program_words ?? 0, memoryBits: candidate?.physical_capacity_bits ?? 0,
    physicalEvidence: profile?.qualification?.path ?? '',
    setupNs: qualified ? physical.physical_metrics.checked.timing__setup__ws : null,
    holdNs: qualified ? physical.physical_metrics.checked.timing__hold__ws : null,
    tools: qualified ? Object.entries(physical.pdk).map(([name, value]) => ({ name, version: String(value) })) : [] };
}
