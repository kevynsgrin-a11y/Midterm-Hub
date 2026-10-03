/**
 * Test-only module resolver for the app layer.
 *
 * `app/` and `lib/` are written for the Next.js bundler, so they use the `@/*`
 * path alias and a bare JSON import. `node --test` has neither, so importing
 * `lib/data.ts` directly fails with ERR_MODULE_NOT_FOUND. This installs the
 * two customisation hooks the bundler would otherwise provide — alias
 * resolution and extension-less/JSON loading — and nothing else. It rewrites no
 * source and no test assertion.
 *
 * Import the module under test through `importFromRepo` *after* importing this
 * file, so the hooks are registered before resolution happens.
 */
import { registerHooks } from 'node:module';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

// tests/frontend/resolve-repo.mjs -> repository root
const repoRoot = new URL('../../', import.meta.url);
const CANDIDATES = ['', '.ts', '.tsx', '.mjs', '.js', '/index.ts', '/index.tsx'];

function firstExisting(base) {
  for (const suffix of CANDIDATES) {
    const candidate = base + suffix;
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return null;
}

let installed = false;

function install() {
  if (installed) return;
  installed = true;
  registerHooks({
    resolve(specifier, context, next) {
      let base;
      if (specifier.startsWith('@/')) base = fileURLToPath(new URL(specifier.slice(2), repoRoot));
      else if (specifier.startsWith('.') && context.parentURL) base = fileURLToPath(new URL(specifier, context.parentURL));
      else return next(specifier, context);
      const found = firstExisting(base.replace(/\/+$/, ''));
      return found ? { url: pathToFileURL(found).href, shortCircuit: true } : next(specifier, context);
    },
    load(url, context, next) {
      // `import payload from "@/generated/elections.json"` carries no import
      // attribute, so hand the JSON back as a plain default-exporting module.
      if (url.endsWith('.json')) {
        const source = `export default ${readFileSync(fileURLToPath(url), 'utf8')};\n`;
        return { format: 'module', source, shortCircuit: true };
      }
      return next(url, context);
    },
  });
}

/** Import a repository module with the bundler-style `@/` alias resolved. */
export function importFromRepo(specifier) {
  install();
  return import(specifier);
}
