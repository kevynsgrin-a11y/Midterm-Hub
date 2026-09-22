import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// The host installs requirements.txt into .venv; never skip data validation.
// Prefer that isolated environment over an ambient PYTHON or system interpreter.
export function interpreterCandidates({ cwd = process.cwd(), platform = process.platform, python = process.env.PYTHON } = {}) {
  return [resolve(cwd, '.venv', platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'), python, 'python3', 'python'].filter(Boolean);
}
const probeCode = 'import sys; assert sys.version_info >= (3, 11); import yaml; from pydantic import BaseModel, ValidationInfo, field_validator, model_validator';

export function runGenerator({ interpreters = interpreterCandidates(), spawn = spawnSync, exists = existsSync } = {}) {
for (const candidate of interpreters) {
  if (candidate.includes('/') || candidate.includes('\\')) {
    if (!exists(candidate)) continue;
  }
  const probe = spawn(candidate, ['-c', probeCode], { windowsHide: true, stdio: 'ignore' });
  if (probe.status !== 0) continue;
  const result = spawn(candidate, ['scripts/build-frontend-data.py'], { windowsHide: true, stdio: 'inherit' });
  return result.status ?? 1;
}
// Retain the original uv workflow for contributors who already use it.
const result = spawn('uv', ['run', '--with-requirements', 'requirements.txt', 'python', 'scripts/build-frontend-data.py'], { windowsHide: true, stdio: 'inherit' });
if (result.error) console.error('Data validation requires Python 3.11+ with requirements.txt installed, or uv. Set PYTHON to your prepared interpreter.');
return result.status ?? 1;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) process.exit(runGenerator());
