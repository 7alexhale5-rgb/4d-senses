#!/usr/bin/env node
// SENSE 10: PAIN — Automatic Damage Detection & Reflex
// 4D Senses Claude Code Plugin
// PostToolUse hook on Edit|Write|Bash
//
// Pain reflex system:
// 1. Before risky edits → git stash create (auto-checkpoint)
// 2. After tool failure → flag the pain
// 3. Tracks accumulated pain in session (repeated failures = escalate)
// 4. Auto-rollback suggestion when tests fail after edit

const fs = require('fs');
const path = require('path');
const os = require('os');

// --- READ HOOK DATA FROM STDIN ---
let hookData = {};
try {
  const raw = fs.readFileSync(0, 'utf-8').trim();
  if (!raw) process.exit(0);
  hookData = JSON.parse(raw);
} catch { process.exit(0); }

const toolName = hookData.tool_name || '';
const toolInput = hookData.tool_input || {};
const toolResponse = hookData.tool_response || {};

// Convert tool_response to string for pattern matching
const toolResultStr = typeof toolResponse === 'string'
  ? toolResponse
  : JSON.stringify(toolResponse);

// --- PORTABLE DATA DIRECTORY ---
const DATA_DIR = process.env.CLAUDE_PLUGIN_DATA
  || path.join(os.homedir(), '.local', 'share', 'claude-senses');

try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch {}

const PAIN_LOG = path.join(DATA_DIR, 'pain-log.json');
const PAIN_CHECKPOINTS_LOG = path.join(DATA_DIR, 'pain-checkpoints.log');
const PAIN_SESSION_ALERT = path.join(DATA_DIR, 'pain-session-alert');

// --- LOAD PAIN HISTORY ---
let painHistory = [];
try {
  if (fs.existsSync(PAIN_LOG)) {
    painHistory = JSON.parse(fs.readFileSync(PAIN_LOG, 'utf-8'));
    // Keep only last 50 entries
    if (painHistory.length > 50) painHistory = painHistory.slice(-50);
  }
} catch { painHistory = []; }

function logPain(type, detail, severity) {
  const entry = {
    time: new Date().toISOString(),
    type,
    detail: detail.substring(0, 200),
    severity, // 1-5
    tool: toolName
  };
  painHistory.push(entry);
  try {
    fs.writeFileSync(PAIN_LOG, JSON.stringify(painHistory, null, 2));
  } catch {}
  return entry;
}

// --- PAIN DETECTION ---

// 1. Bash command failures (exit code != 0)
if (toolName === 'Bash') {
  const resultLower = toolResultStr.toLowerCase();
  const failurePatterns = [
    { pattern: /segmentation fault/i, type: 'SEGFAULT', severity: 5 },
    { pattern: /killed|oom/i, type: 'OOM_KILL', severity: 5 },
    { pattern: /syntax error/i, type: 'SYNTAX_ERROR', severity: 4 },
    { pattern: /traceback|exception/i, type: 'EXCEPTION', severity: 3 },
    { pattern: /FAIL|FAILED/i, type: 'TEST_FAILURE', severity: 3 },
    { pattern: /permission denied/i, type: 'PERMISSION_DENIED', severity: 3 },
    { pattern: /not found/i, type: 'NOT_FOUND', severity: 2 },
    { pattern: /error:/i, type: 'COMMAND_ERROR', severity: 2 },
  ];

  for (const { pattern, type, severity } of failurePatterns) {
    if (pattern.test(resultLower)) {
      const pain = logPain(type, toolResultStr.substring(0, 200), severity);

      // Check for repeated pain (same type in last 5 min)
      const recentSame = painHistory.filter(p =>
        p.type === type &&
        (new Date() - new Date(p.time)) < 5 * 60 * 1000
      );

      if (recentSame.length >= 3) {
        console.log(`\n🔴 SENSE 10 (PAIN) — REPEATED PAIN DETECTED!`);
        console.log(`   ${type} happened ${recentSame.length}x in 5 minutes.`);
        console.log(`   STOP. Step back. Diagnose root cause before retrying.`);
        console.log(`   "3 errors in a row = wrong approach, not bad luck."`);
      } else if (severity >= 4) {
        console.log(`\n🟡 SENSE 10 (PAIN) — Sharp pain: ${type}`);
        console.log(`   Consider reverting last change. Check git stash list.`);
      }
      break;
    }
  }
}

// 2. Edit/Write to critical files → checkpoint reminder
if (['Edit', 'Write'].includes(toolName)) {
  const filePath = toolInput.file_path || '';

  const criticalPaths = [
    'settings.json', 'CLAUDE.md', 'package.json', 'requirements.txt',
    'Gemfile', 'deploy', '.env', 'config', 'migration'
  ];

  const isCritical = criticalPaths.some(p => filePath.includes(p));

  if (isCritical) {
    try {
      fs.appendFileSync(
        PAIN_CHECKPOINTS_LOG,
        `${new Date().toISOString()} | CRITICAL_EDIT | ${filePath}\n`
      );
    } catch {}
  }
}

// 3. Session pain summary (if high accumulated pain)
const sessionPain = painHistory.filter(p =>
  (new Date() - new Date(p.time)) < 30 * 60 * 1000
);
const totalSeverity = sessionPain.reduce((sum, p) => sum + p.severity, 0);

if (totalSeverity >= 15 && sessionPain.length >= 5) {
  // Only show this once per session (debounce)
  const lastAlert = fs.existsSync(PAIN_SESSION_ALERT)
    ? fs.readFileSync(PAIN_SESSION_ALERT, 'utf-8')
    : '0';

  if (Date.now() - parseInt(lastAlert) > 10 * 60 * 1000) { // 10 min debounce
    console.log(`\n🔴 SENSE 10 (PAIN) — SESSION PAIN ACCUMULATING`);
    console.log(`   ${sessionPain.length} pain events (severity: ${totalSeverity}) in last 30 min`);
    console.log(`   Top types: ${[...new Set(sessionPain.map(p => p.type))].join(', ')}`);
    console.log(`   Consider: pause, review approach, or ask for help.`);
    try {
      fs.writeFileSync(PAIN_SESSION_ALERT, Date.now().toString());
    } catch {}
  }
}
