#!/usr/bin/env node
// SENSE 8: SMELL — Code Smell Detector
// 4D Senses Claude Code Plugin
// PostToolUse hook on Edit|Write
//
// Detects code smells in files being written/edited:
// - God file (>500 lines for code, >1000 for config/data)
// - Deep nesting (>5 levels)
// - Duplication (3+ identical non-trivial lines)
// - Hardcoded secrets/keys
// - Console.log pollution (>5 in non-debug files)
// - TODO/FIXME accumulation (>3 markers)

const fs = require('fs');
const path = require('path');

// Read hook data from stdin
let hookData = {};
try {
  const raw = fs.readFileSync(0, 'utf-8').trim();
  if (!raw) process.exit(0);
  hookData = JSON.parse(raw);
} catch { process.exit(0); }

const toolName = hookData.tool_name || '';
const toolInput = hookData.tool_input || {};

// Only fire on Edit/Write
if (!['Edit', 'Write'].includes(toolName)) process.exit(0);

const filePath = toolInput.file_path || '';
if (!filePath || !fs.existsSync(filePath)) process.exit(0);

// Skip files larger than 2MB (avoid reading huge generated files)
try { if (fs.statSync(filePath).size > 2 * 1024 * 1024) process.exit(0); } catch { process.exit(0); }

// Skip non-code files
const codeExts = ['.js', '.ts', '.py', '.rb', '.jsx', '.tsx', '.sh', '.css', '.html', '.json', '.md'];
const ext = path.extname(filePath).toLowerCase();
if (!codeExts.includes(ext)) process.exit(0);

// Skip skill files and memory files (they're supposed to be long)
if (filePath.includes('/skills/') && filePath.endsWith('SKILL.md')) process.exit(0);
if (filePath.includes('/memory/')) process.exit(0);

// Wave 1 (refactored 2026-04-15 post-audit): shared skip-path predicate.
// sense-8 skips test files — god-file/duplication metrics don't apply to fixtures.
const { shouldSkipPath } = require('./lib/skip-paths');
if (shouldSkipPath(filePath, { skipTests: true })) process.exit(0);

let content;
try {
  content = fs.readFileSync(filePath, 'utf-8');
} catch { process.exit(0); }

const lines = content.split('\n');
const smells = [];

// 1. God file (>500 lines for code, >1000 for config/data)
const lineLimit = ['.json', '.md', '.html'].includes(ext) ? 1000 : 500;
if (lines.length > lineLimit) {
  smells.push(`GOD FILE: ${lines.length} lines (limit: ${lineLimit}). Consider splitting.`);
}

// 2. Deep nesting (>5 levels of indentation)
const indentSize = ['.py', '.rb'].includes(ext) ? 4 : 2; // Python/Ruby use 4-space
const maxNesting = lines.reduce((max, line) => {
  if (line.trim() === '') return max;
  const indent = line.match(/^(\s*)/)[1].length;
  const level = Math.floor(indent / indentSize);
  return Math.max(max, level);
}, 0);
if (maxNesting > 5) {
  smells.push(`DEEP NESTING: ${maxNesting} levels detected. Extract functions to reduce complexity.`);
}

// 3. Duplication detection (3+ identical non-trivial lines)
if (ext !== '.json' && ext !== '.md') {
  const lineCounts = {};
  lines.forEach(line => {
    const trimmed = line.trim();
    if (trimmed.length > 20 && !trimmed.startsWith('//') && !trimmed.startsWith('#') && !trimmed.startsWith('*')) {
      lineCounts[trimmed] = (lineCounts[trimmed] || 0) + 1;
    }
  });
  const dupes = Object.entries(lineCounts).filter(([, count]) => count >= 3);
  if (dupes.length > 0) {
    smells.push(`DUPLICATION: ${dupes.length} line(s) repeated 3+ times. DRY violation.`);
  }
}

// 4. Hardcoded secrets/keys pattern
const secretPatterns = [
  /(?:=|:|=>)\s*['"][A-Za-z0-9]{32,}['"]/,  // Long random strings in assignments (potential keys)
  /sk-[a-zA-Z0-9]{20,}/,       // OpenAI-style keys
  /Bearer [a-zA-Z0-9]+/,       // Auth tokens inline
  /password\s*[:=]\s*['"][^'"]+['"]/i, // Hardcoded passwords
];
if (ext !== '.md' && ext !== '.json') {
  const secretLines = lines.filter(line =>
    secretPatterns.some(p => p.test(line)) && !line.trim().startsWith('//') && !line.trim().startsWith('#')
  );
  if (secretLines.length > 0) {
    smells.push(`SECRETS: ${secretLines.length} line(s) may contain hardcoded credentials. Use env vars.`);
  }
}

// 5. Console.log pollution (>5 in non-debug files)
if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
  const consoleLogs = lines.filter(l => l.includes('console.log') && !l.trim().startsWith('//'));
  if (consoleLogs.length > 5) {
    smells.push(`CONSOLE POLLUTION: ${consoleLogs.length} console.log statements. Clean before shipping.`);
  }
}

// 6. TODO/FIXME accumulation
const todos = lines.filter(l => /\b(TODO|FIXME|HACK|XXX|TEMP)\b/i.test(l));
if (todos.length > 3) {
  smells.push(`TECH DEBT: ${todos.length} TODO/FIXME/HACK markers. Address before they rot.`);
}

// Output smells as additionalContext
if (smells.length > 0) {
  const severity = smells.length >= 3 ? 'STINKS' : smells.length >= 2 ? 'WHIFF' : 'FAINT';
  const msg = `SENSE 8 (SMELL) ${severity} — ${path.basename(filePath)}\n` + smells.map(s => `  • ${s}`).join('\n');
  console.log(msg);
}
