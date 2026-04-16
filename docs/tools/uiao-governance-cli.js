#!/usr/bin/env node
/**
 * UIAO Governance CLI
 * Local drift inspection and metadata validation
 * Usage: node tools/uiao-governance-cli.js [--dir docs]
 */

import fs from "fs";
import path from "path";
import yaml from "js-yaml";

const ROOT = process.cwd();
const DOCS_DIR = process.argv[2] === "--dir" ? process.argv[3] : path.join(ROOT, "docs");

function findMarkdownFiles(dir) {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  for (const file of fs.readdirSync(dir)) {
    const full = path.join(dir, file);
    if (fs.statSync(full).isDirectory()) {
      results = results.concat(findMarkdownFiles(full));
    } else if (file.endsWith(".md")) {
      results.push(full);
    }
  }
  return results;
}

function parseFrontmatter(content) {
  const match = /^---\n([\s\S]*?)\n---/.exec(content);
  if (!match) return null;
  try { return yaml.load(match[1]); } catch { return null; }
}

function validateMetadata(meta, file) {
  const errors = [];
  const required = ["id", "title", "owner", "status"];
  for (const field of required) {
    if (!meta[field]) errors.push("Missing required field: " + field);
  }
  const deprecated = ["category", "tags_old"];
  for (const field of deprecated) {
    if (meta[field]) errors.push("Deprecated field present: " + field);
  }
  if (meta.id && !/^[a-z][a-z0-9\-]+$/.test(meta.id)) {
    errors.push("Invalid ID format: " + meta.id);
  }
  return errors;
}

function run() {
  console.log("UIAO Governance -- Local Drift Inspection\n");
  const files = findMarkdownFiles(DOCS_DIR);
  let totalErrors = 0;
  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    const meta = parseFrontmatter(content);
    if (!meta) {
      console.log("  WARN  No frontmatter: " + file);
      totalErrors++;
      continue;
    }
    const errors = validateMetadata(meta, file);
    if (errors.length > 0) {
      console.log("  FAIL  " + file);
      errors.forEach(e => console.log("       - " + e));
      totalErrors += errors.length;
    }
  }
  if (totalErrors === 0) {
    console.log("\nNo drift detected. Metadata is clean.");
  } else {
    console.log("\nTotal issues: " + totalErrors);
    process.exit(1);
  }
}

run();
