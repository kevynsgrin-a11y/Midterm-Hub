import assert from 'node:assert/strict';
import test from 'node:test';
import { importFromRepo } from './resolve-repo.mjs';

const { cn } = await importFromRepo('../../lib/utils.ts');

test('conflicting Tailwind utilities resolve to the last one supplied', () => {
  assert.equal(cn('px-2', 'px-4'), 'px-4');
  // `text-sm` and `text-lg` conflict, so the earlier size is dropped while the
  // differently-grouped colour utility survives.
  assert.equal(cn('text-sm text-muted-foreground', 'text-lg'), 'text-muted-foreground text-lg');
  assert.equal(cn('p-2', 'p-4', 'p-6'), 'p-6');
});

test('non-conflicting utilities are all preserved in order', () => {
  assert.equal(cn('flex', 'items-center', 'gap-2'), 'flex items-center gap-2');
});

test('conditional class inputs are flattened, and falsy entries disappear', () => {
  assert.equal(cn('a', false && 'b', ['c', { d: true, e: false }], null, undefined), 'a c d');
  assert.equal(cn(false, null, undefined, ''), '');
  assert.equal(cn(), '');
});

test('variant-prefixed utilities override their unprefixed counterpart', () => {
  assert.equal(cn('hidden', 'md:block'), 'hidden md:block');
  assert.equal(cn('md:block', 'hidden'), 'md:block hidden');
});

test('a base class and its responsive override collapse to the responsive one', () => {
  assert.equal(cn('p-2 md:p-8', 'md:p-10'), 'p-2 md:p-10');
});
