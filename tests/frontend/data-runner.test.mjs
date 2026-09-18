import assert from 'node:assert/strict';
import test from 'node:test';
import { runGenerator } from '../../scripts/run-data.mjs';

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
