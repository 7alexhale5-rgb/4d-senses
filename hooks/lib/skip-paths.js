// Shared skip-path predicates for 4D sense hooks.
// Single source of truth for "is this file worth analyzing?" — eliminates
// the drift risk from copy-pasting regexes across sense-8/10/15.
//
// Add a new skip dir here (e.g. `.vercel`, `.svelte-kit`) and all three
// hooks pick it up on next fire.

'use strict';

const SKIP_DIRS_RE = /(^|\/)(node_modules|dist|build|\.next|\.turbo|\.vercel|coverage|__pycache__|\.venv|target|out)\//;
const TEST_FILES_RE = /\.(test|spec)\.(ts|tsx|js|jsx|py)$/i;

// Should this file path be skipped entirely by a sense hook?
//
// filePath: absolute or relative path.
// opts.skipTests (default false): also skip test/spec files.
//   Intentional asymmetry across senses:
//   - sense-8 (smell):     skipTests=true  (metrics don't apply to fixtures)
//   - sense-10 (pain):     skipTests=false (test failures ARE real pain)
//   - sense-15 (intuition): skipTests=true (feedback patterns rarely apply)
//
// Returns boolean.
function shouldSkipPath(filePath, opts = {}) {
  if (!filePath) return false; // Can't decide — let the hook run its own checks.
  if (SKIP_DIRS_RE.test(filePath)) return true;
  if (opts.skipTests && TEST_FILES_RE.test(filePath)) return true;
  return false;
}

module.exports = { shouldSkipPath, SKIP_DIRS_RE, TEST_FILES_RE };
