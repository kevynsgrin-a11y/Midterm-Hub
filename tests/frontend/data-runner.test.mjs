import assert from 'node:assert/strict';
import test from 'node:test';
import { resolve } from 'node:path';
import { interpreterCandidates, runGenerator } from '../../scripts/run-data.mjs';

for (const platform of ['linux', 'win32']) {
  test(`the checkout environment wins over an ambient Python on ${platform}`, () => {
    const prepared = resolve('.venv', platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
    const calls = [];
    const code = runGenerator({
      interpreters: interpreterCandidates({ platform, python: 'ambient-python' }),
      exists: () => true,
      spawn(command, args) {
        calls.push([command, args]);
        return { status: 0 };
      },
    });
    assert.equal(code, 0);
    assert.deepEqual(calls.map(([command]) => command), [prepared, prepared]);
    assert.deepEqual(calls[1][1], ['scripts/build-frontend-data.py']);
  });
}

test('a missing checkout environment still allows a prepared explicit Python', () => {
  const calls = [];
  const code = runGenerator({
    interpreters: interpreterCandidates({ python: 'prepared-python' }),
    exists: () => false,
    spawn(command) {
      calls.push(command);
      return { status: 0 };
    },
  });
  assert.equal(code, 0);
  assert.deepEqual(calls, ['prepared-python', 'prepared-python']);
});

test('skip an incompatible interpreter and use the prepared candidate', () => {
  const calls = [];
  const code = runGenerator({ interpreters: ['legacy', 'prepared'], spawn(command, args) {
    calls.push([command, args]);
    if (args[0] === '-c') return { status: command === 'legacy' ? 1 : 0 };
    return { status: 0 };
  } });
  assert.equal(code, 0);
  assert.deepEqual(calls.map(([command]) => command), ['legacy', 'prepared', 'prepared']);
  assert.match(calls[0][1][1], /sys\.version_info >= \(3, 11\)/);
  assert.match(calls[0][1][1], /ValidationInfo, field_validator, model_validator/);
});

test('all incompatible interpreters fall back to uv', () => {
  const calls = [];
  assert.equal(runGenerator({ interpreters: ['legacy'], spawn(command) {
    calls.push(command); return { status: command === 'uv' ? 0 : 1 };
  } }), 0);
  assert.deepEqual(calls, ['legacy', 'uv']);
});

test('a real data validation failure stops without trying another interpreter', () => {
  const calls = [];
  assert.equal(runGenerator({ interpreters: ['prepared', 'other'], spawn(command, args) {
    calls.push(command); return { status: args[0] === '-c' ? 0 : 42 };
  } }), 42);
  assert.deepEqual(calls, ['prepared', 'prepared']);
});
