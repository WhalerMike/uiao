#!/usr/bin/env node
// update_corpus_index.js
// Scans docs/**/*.md, extracts UIAO frontmatter, writes docs/_data/corpus-index.json
// Run: node scripts/update_corpus_index.js
// CI: triggered on push to main when docs/**/*.md changes

const fs = require('fs');
const path = require('path');
const child_process = require('child_process');

const ROOT = process.cwd();
const DOCS_DIR = path.join(ROOT, 'docs');
const INDEX_PATH = path.join(DOCS_DIR, '_data', 'corpus-index.json');

// Recursively collect all .md files under dir
function getMarkdownFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  let files = [];
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      files = files.concat(getMarkdownFiles(full));
    } else if (e.isFile() && e.name.endsWith('.md')) {
      files.push(full);
    }
  }
  return files;
}

// Parse YAML frontmatter between first pair of --- delimiters
function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;
  const yaml = match[1];
  const data = {};
  let currentKey = null;
  for (const line of yaml.split('\n')) {
    if (/^\s*$/.test(line)) continue;
    const keyMatch = line.match(/^([A-Za-z0-9_.]+):\s*(.*)$/);
    if (keyMatch) {
      currentKey = keyMatch[1];
      let val = keyMatch[2].trim();
      if (val.startsWith('"') || val.startsWith("'")) val = val.slice(1, -1);
      data[currentKey] = val;
    } else if (currentKey && /^\s+-\s*(.*)$/.test(line)) {
      if (!Array.isArray(data[currentKey])) data[currentKey] = [];
      data[currentKey].push(line.replace(/^\s+-\s*/, '').trim());
    }
  }
  return data;
}

// Get the short git commit hash for a file
function getShortCommitHash(filePath) {
  try {
    const rel = path.relative(ROOT, filePath);
    return child_process
      .execSync('git log -n 1 --pretty=format:%h -- "' + rel + '"', { encoding: 'utf8' })
      .trim() || null;
  } catch (_) {
    return null;
  }
}

function main() {
  const files = getMarkdownFiles(DOCS_DIR);
  const entries = [];

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    const fm = parseFrontmatter(content);
    if (!fm) continue;

    // Accept uiao_id, uiao.id, or id fields
    const id = fm['uiao_id'] || fm['uiao.id'] || fm['id'] || null;
    if (!id || !/^UIAO_[A-Z]_[0-9]{2,}$/.test(id)) continue;

    const title = fm['title'] || id;
    const appendix = id.split('_')[1] || '';
    const status = fm['status'] || 'Draft';
    const owner = fm['owner'] || '';
    const tags = Array.isArray(fm['tags']) ? fm['tags'] : (fm['tags'] ? [fm['tags']] : []);
    const lastUpdated = fm['lastUpdated'] || new Date().toISOString().slice(0, 10);
    const relPath = path.relative(DOCS_DIR, file).replace(/\\/g, '/');
    const commit = getShortCommitHash(file);

    entries.push({ id, title, appendix, status, owner, lastUpdated, path: relPath, tags, commit });
  }

  entries.sort((a, b) => a.id.localeCompare(b.id));

  fs.mkdirSync(path.dirname(INDEX_PATH), { recursive: true });
  fs.writeFileSync(INDEX_PATH, JSON.stringify(entries, null, 2) + '\n', 'utf8');
  console.log('Updated corpus index: ' + entries.length + ' entries -> ' + INDEX_PATH);
}

main();
