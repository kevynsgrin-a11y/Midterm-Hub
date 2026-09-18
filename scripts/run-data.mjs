import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

// The host must install requirements.txt; never silently skip data validation.
// Prefer the checkout's venv, then an explicitly configured/system Python.
const candidates = [process.env.PYTHON, resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'), 'python3', 'python'].filter(Boolean);
for (const candidate of candidates) {
  if (candidate.includes('/') || candidate.includes('\\')) {
    if (!existsSync(candidate)) continue;
  }
  const probe = spawnSync(candidate, ['-c', 'import yaml, pydantic'], { windowsHide: true, stdio: 'ignore' });
  if (probe.status !== 0) continue;
  const result = spawnSync(candidate, ['scripts/build-frontend-data.py'], { windowsHide: true, stdio: 'inherit' });
  process.exit(result.status ?? 1);
}
// Retain the original uv workflow for contributors who already use it.
const result = spawnSync('uv', ['run', '--with-requirements', 'requirements.txt', 'python', 'scripts/build-frontend-data.py'], { windowsHide: true, stdio: 'inherit' });
if (result.error) console.error('Data validation requires Python 3.11+ with requirements.txt installed, or uv. Set PYTHON to your prepared interpreter.');
process.exit(result.status ?? 1);
