#!/usr/bin/env node
// SENSE 15: INTUITION — Pre-Rational Pattern Matching
// 4D Senses Claude Code Plugin
// PostToolUse hook on Edit|Write|Bash
//
// Reads feedback memory files + pain log to detect:
// - Patterns that match past mistakes
// - Risky operations that caused problems before
// - File types/paths associated with past pain
// - Repeated approaches that failed before

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// --- Parse stdin JSON (Claude Code hooks deliver data this way) ---
let hookData = {};
try {
  const raw = fs.readFileSync(0, 'utf-8').trim();
  if (!raw) process.exit(0);
  hookData = JSON.parse(raw);
} catch { process.exit(0); }

const toolName = hookData.tool_name || '';
const toolInput = hookData.tool_input || {};

// Only fire on code-modifying operations
if (!['Edit', 'Write', 'Bash'].includes(toolName)) process.exit(0);

// --- Derive paths portably (no hardcoded usernames) ---

// Feedback memory: resolve per-project based on cwd reported by the hook
const cwd = hookData.cwd || process.cwd();
const projectKey = cwd.replace(/\//g, '-').replace(/^-/, '');
const FEEDBACK_DIR = process.env.CLAUDE_SENSES_MEMORY_DIR
  || path.join(os.homedir(), '.claude', 'projects', projectKey, 'memory');

// Plugin data directory (pain log, debounce file)
const DATA_DIR = process.env.CLAUDE_PLUGIN_DATA
  || path.join(os.homedir(), '.local', 'share', 'claude-senses');
try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch {}

const PAIN_LOG     = path.join(DATA_DIR, 'pain-log.json');
const DEBOUNCE_FILE = path.join(DATA_DIR, 'sense-15-debounce.json');

// Cache lives in /tmp — appropriate for a short-lived cache
const CACHE_FILE   = '/tmp/sense15-lessons-cache.json';
const CACHE_TTL_MS = 60 * 1000; // 60-second TTL

// --- Load feedback lessons with mtime-based caching ---
let lessons = [];
try {
  let useCache = false;
  if (fs.existsSync(CACHE_FILE)) {
    const cacheStat = fs.statSync(CACHE_FILE);
    if (Date.now() - cacheStat.mtimeMs < CACHE_TTL_MS) {
      lessons = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8'));
      useCache = true;
    }
  }
  if (!useCache && fs.existsSync(FEEDBACK_DIR)) {
    const files = fs.readdirSync(FEEDBACK_DIR).filter(f => f.startsWith('feedback_'));
    for (const file of files) {
      const content = fs.readFileSync(path.join(FEEDBACK_DIR, file), 'utf-8');
      const lines = content.split('\n')
        .filter(l =>
          l.trim().length > 20 &&
          !l.startsWith('---') &&
          !l.startsWith('name:') &&
          !l.startsWith('description:') &&
          !l.startsWith('type:')
        )
        .map(l => l.toLowerCase());
      lessons.push(...lines);
    }
    try { fs.writeFileSync(CACHE_FILE, JSON.stringify(lessons)); } catch {}
  }
} catch {}

// --- Load recent pain history ---
let painHistory = [];
try {
  if (fs.existsSync(PAIN_LOG)) {
    painHistory = JSON.parse(fs.readFileSync(PAIN_LOG, 'utf-8'));
  }
} catch {}

// --- Extract the subject of this tool call ---
const filePath = toolInput.file_path || toolInput.command || '';
const filePathLower = filePath.toLowerCase();

// --- INTUITION PATTERNS ---

const warnings = [];

// 1. Match current action against past feedback lessons (keyword overlap)
const actionKeywords = filePathLower.split(/[\s/._-]+/).filter(w => w.length > 3);
for (const lesson of lessons) {
  const matchedWords = actionKeywords.filter(w => lesson.includes(w));
  if (matchedWords.length >= 2) {
    warnings.push({
      type: 'FEEDBACK_MATCH',
      message: `Past feedback matches: "${lesson.substring(0, 120)}..."`,
      confidence: matchedWords.length >= 3 ? 'HIGH' : 'MEDIUM'
    });
    break; // One match is enough to surface
  }
}

// 2. Pain deja vu — repeated failures in the same area
if (painHistory.length > 0) {
  const painPaths = painHistory
    .filter(p => p.detail)
    .map(p => p.detail.toLowerCase());

  const relevantPain = painPaths.filter(pp =>
    actionKeywords.some(w => pp.includes(w))
  );

  if (relevantPain.length >= 2) {
    warnings.push({
      type: 'PAIN_DEJA_VU',
      message: `This area caused ${relevantPain.length} pain events recently. Tread carefully.`,
      confidence: 'MEDIUM'
    });
  }
}

// 3. Known risky patterns
// Note: rm -rf, force push, DROP TABLE are already blocked by block-destructive.sh (PreToolUse).
// Only patterns NOT covered by that hook belong here.
const riskyPatterns = [
  { pattern: /migrate|migration/i,                                   warning: 'Migration detected. Test rollback path.' },
  { pattern: /\.env|secret|\bapi.?key\b|token|password|credential/i, warning: 'Sensitive file. Check for accidental exposure.' },
  { pattern: /rsync.*--delete/i,                                      warning: 'Rsync with --delete. Verify target.' },
];

if (toolName === 'Bash' && toolInput.command) {
  for (const { pattern, warning } of riskyPatterns) {
    if (pattern.test(toolInput.command)) {
      warnings.push({
        type: 'RISKY_PATTERN',
        message: warning,
        confidence: 'HIGH'
      });
    }
  }
}

// 4. Late-night critical file warning (1AM–5AM)
const hour = new Date().getHours();
if (hour >= 1 && hour <= 5) {
  const criticalPatterns = ['deploy', 'prod', 'config', 'settings', '.env', 'migration'];
  if (criticalPatterns.some(p => filePathLower.includes(p))) {
    warnings.push({
      type: 'LATE_NIGHT_CRITICAL',
      message: `It's ${hour}AM and you're editing critical files. Sleep > shipping.`,
      confidence: 'LOW'
    });
  }
}

// --- Output warnings with 5-minute debounce per type ---
if (warnings.length > 0) {
  let debounce = {};
  try {
    if (fs.existsSync(DEBOUNCE_FILE)) {
      debounce = JSON.parse(fs.readFileSync(DEBOUNCE_FILE, 'utf-8'));
    }
  } catch {}

  const now = Date.now();
  const newWarnings = warnings.filter(w => {
    const lastTime = debounce[w.type] || 0;
    return (now - lastTime) > 5 * 60 * 1000;
  });

  if (newWarnings.length > 0) {
    newWarnings.forEach(w => { debounce[w.type] = now; });
    try { fs.writeFileSync(DEBOUNCE_FILE, JSON.stringify(debounce)); } catch {}

    console.log('\n🔮 SENSE 15 (INTUITION) — Pattern Match Alert');
    newWarnings.forEach(w => {
      const icon = w.confidence === 'HIGH' ? '🔴' : w.confidence === 'MEDIUM' ? '🟡' : '🟢';
      console.log(`   ${icon} [${w.type}] ${w.message}`);
    });
  }
}
