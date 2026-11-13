/* SPDX-License-Identifier: Apache-2.0 */
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { repoRoot } from '../tools/export_atlas.mjs';
const read = (name) => JSON.parse(readFileSync(resolve(repoRoot, name), 'utf8'));

export function failedActiveQualification() {
  const profilePath = 'tools/production-profile.json';
  if (existsSync(resolve(repoRoot, profilePath))) {
    const profile = read(profilePath);
    const path = profile.qualification.path;
    const qualification = read(path);
    qualification.jobs.gl_test.conclusion = 'failure';
    const raw = JSON.stringify(qualification);
    // Rehash the changed report so this exercises the failed-job condition,
    // rather than merely detecting an outdated checksum.
    profile.qualification.sha256 = createHash('sha256').update(raw).digest('hex');
    return { id: 'E0045', overrides: { [path]: raw, [profilePath]: JSON.stringify(profile) } };
  }
  const path = 'evidence/E0018-uart-rx-public/qualification.json';
  const qualification = read(path);
  qualification.runs.push_test.conclusion = 'failure';
  return { id: 'E0018', overrides: { [path]: JSON.stringify(qualification) } };
}

export function missingQualificationOverrides() {
  const overrides = {
    'evidence/E0010-pinned-cmos5l-run/result.json': null,
    'evidence/E0016-uart-tx-8n1/ci-manifest.json': null,
    'evidence/E0018-uart-rx-public/ci-manifest.json': null,
  };
  if (existsSync(resolve(repoRoot, 'tools/production-profile.json'))) {
    overrides[read('tools/production-profile.json').qualification.path] = null;
  }
  return overrides;
}
