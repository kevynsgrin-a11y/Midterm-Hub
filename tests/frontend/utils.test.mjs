import assert from 'node:assert/strict';
import test from 'node:test';
import { cn } from '../../lib/utils.ts';

test('a later conflicting tailwind utility wins and the earlier one is dropped', () => {
  // The whole point of twMerge: component callers override a base class instead of
  // shipping both and letting stylesheet order decide.
  assert.equal(cn('p-2', 'p-4'), 'p-4');
  assert.equal(cn('text-sm text-red-500', 'text-lg'), 'text-red-500 text-lg');
  // A narrower group is kept alongside the broader one it does not conflict with.
  assert.equal(cn('px-2', 'px-4', 'pl-8'), 'px-4 pl-8');
});

test('non-conflicting classes are all preserved in order', () => {
  assert.equal(cn('rounded border', 'shadow'), 'rounded border shadow');
  assert.equal(cn('flex', 'items-center', 'gap-2'), 'flex items-center gap-2');
});

test('falsy inputs are dropped and no separators leak in', () => {
  assert.equal(cn('a', false, null, undefined, 'b'), 'a b');
  assert.equal(cn('a', false), 'a');
  assert.equal(cn(false, null, undefined), '');
  assert.equal(cn(), '');
  // 0 is falsy and must not become the literal class "0".
  assert.equal(cn('a', 0, ''), 'a');
});

test('clsx object and array forms compose before merging', () => {
  assert.equal(cn(['flex', 'p-2'], { 'font-bold': true, hidden: false }), 'flex p-2 font-bold');
  assert.equal(cn({ 'p-2': true, 'p-4': true }), 'p-4');
  assert.equal(cn([['a', ['b', 'c']]]), 'a b c');
});

test('arbitrary values and modifiers merge by real tailwind groups', () => {
  assert.equal(cn('bg-[#fff]', 'bg-[#000]'), 'bg-[#000]');
  assert.equal(cn('hover:p-2', 'hover:p-4'), 'hover:p-4');
  // Different variant groups are independent, so both survive.
  assert.equal(cn('p-2', 'hover:p-4'), 'p-2 hover:p-4');
});

test('arbitrary property syntax and non-tailwind names are left alone', () => {
  assert.equal(cn('[grid-area:header]', 'p-2'), '[grid-area:header] p-2');
  assert.equal(cn('card', 'p-2', 'card--wide'), 'card p-2 card--wide');
});
