#!/usr/bin/env node
// scripts/metadata_drift_scan.js
// Produces reports/metadata-drift-YYYY-MM-DD.json with critical and high items.

const fs = require('fs');
const path = require('path');
const child = require('child_process');

const ROOT = process.cwd();
const DOCS = path.join(ROOT, 'docs');
const OUTDIR = path.join(ROOT, 'reports');
if (!fs.existsSync(OUTDIR)) fs.mkdirSync(OUTDIR, { recursive: true });

function nowDate() {
  return new Date().toISOString().slice(0, 10);
}

function run(cmd) {
  try {
    return child.execSync(cmd, { encoding: 'utf8' }).trim();
  } catch (e) {
    return '';
  }
}

// 1) Find invalid uiao.id patterns or missing frontmatter
function findInvalidIds() {
  const out = run('git ls-files ' + DOCS);
  const files = out.split('\n').filter(f => f.endsWith('.md'));
  const invalid = [];
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    const content = fs.readFileSync(f, 'utf8');
    const m = content.match(/^---\n([\s\S]*?)\n---/);
    if (!m) {
      invalid.push({ file: f, reason: 'Missing frontmatter' });
      continue;
    }
    const fm = m[1];
    let id = null;
    const uiaoIdMatch = fm.match(/uiao:[\s\S]*?id:\s*([^\n\r]+)/);
    if (uiaoIdMatch) id = uiaoIdMatch[1].trim().replace(/['"]/g, '');
    else {
      const topId = fm.match(/^\s*id:\s*([^\n\r]+)/m);
      if (topId) id = topId[1].trim().replace(/['"]/g, '');
    }
    if (!id || !/^UIAO_[A-Z_]+_[0-9]{2,}$/.test(id)) {
      invalid.push({ file: f, id: id || null, reason: 'Invalid or missing uiao.id' });
    }
  }
  return invalid;
}

// 2) Find ADRs missing affects
function findAdrsMissingAffects() {
  const adrDir = path.join(DOCS, 'adr');
  if (!fs.existsSync(adrDir)) return [];
  const files = fs.readdirSync(adrDir).filter(n => n.endsWith('.md'));
  const missing = [];
  for (const fn of files) {
    const f = path.join(adrDir, fn);
    const content = fs.readFileSync(f, 'utf8');
    const m = content.match(/^---\n([\s\S]*?)\n---/);
    if (!m) { missing.push({ file: f, reason: 'Missing frontmatter' }); continue; }
    const fm = m[1];
    const affectsMatch = fm.match(/affects:\s*\n([\s\S]*?)(\n[A-Za-z0-9_-]+:|\n---|$)/);
    if (!affectsMatch) {
      missing.push({ file: f, reason: 'Missing affects field' });
    } else {
      const list = affectsMatch[1].match(/UIAO_[A-Z_]+_[0-9]{2,}/g) || [];
      if (list.length === 0) missing.push({ file: f, reason: 'affects present but no valid UIAO ids' });
    }
  }
  return missing;
}

// 3) Find stale docs (lastUpdated older than threshold months)
function findStaleDocs(months) {
  months = months || 12;
  const out = run('git ls-files ' + DOCS);
  const files = out.split('\n').filter(f => f.endsWith('.md'));
  const stale = [];
  const cutoff = new Date();
  cutoff.setMonth(cutoff.getMonth() - months);
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    const content = fs.readFileSync(f, 'utf8');
    const m = content.match(/^---\n([\s\S]*?)\n---/);
    if (!m) continue;
    const fm = m[1];
    const luMatch = fm.match(/lastUpdated:\s*([^\n\r]+)/);
    const lu = luMatch ? luMatch[1].trim().replace(/['"]/g, '') : null;
    const last = lu ? new Date(lu) : null;
    if (!last || isNaN(last) || last < cutoff) {
      stale.push({ file: f, lastUpdated: lu || null });
    }
  }
  return stale;
}

function buildReport() {
  const invalidIds = findInvalidIds();
  const adrsMissing = findAdrsMissingAffects();
  const stale = findStaleDocs(12);

  const critical = [];
  for (const i of invalidIds) critical.push({ severity: 'critical', type: 'invalid-id', file: i.file, reason: i.reason, id: i.id || null });
  for (const a of adrsMissing) critical.push({ severity: 'critical', type: 'adr-missing-affects', file: a.file, reason: a.reason });

  const high = stale.map(s => ({ severity: 'high', type: 'stale', file: s.file, lastUpdated: s.lastUpdated }));

  const report = {
    generatedAt: new Date().toISOString(),
    summary: {
      invalidIds: invalidIds.length,
      adrsMissingAffects: adrsMissing.length,
      staleDocs: stale.length
    },
    critical,
    high
  };

  const outPath = path.join(OUTDIR, 'metadata-drift-' + nowDate() + '.json');
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2), 'utf8');
  console.log('Wrote drift report: ' + outPath);
  console.log(JSON.stringify(report.summary));
  process.exit(0);
}

buildReport();
