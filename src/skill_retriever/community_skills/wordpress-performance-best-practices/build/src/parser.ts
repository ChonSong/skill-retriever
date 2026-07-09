import { readFileSync } from 'fs';
import type { Rule, RuleFrontmatter, Section } from './types.js';
import { sectionPrefixes } from './config.js';

export function parseRuleFile(filepath: string, filename: string): Rule | null {
  const content = readFileSync(filepath, 'utf-8');

  // Parse frontmatter
  const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatterMatch) {
    console.warn(`No frontmatter found in ${filename}`);
    return null;
  }

  const frontmatterStr = frontmatterMatch[1];
  const frontmatter = parseFrontmatter(frontmatterStr);

  if (!frontmatter.title || !frontmatter.impact) {
    console.warn(`Invalid frontmatter in ${filename}`);
    return null;
  }

  // Extract content after frontmatter
  const bodyContent = content.slice(frontmatterMatch[0].length).trim();

  // Determine section from filename prefix
  const prefix = filename.split('-')[0];
  const section = sectionPrefixes[prefix];

  if (!section) {
    console.warn(`Unknown section prefix in ${filename}`);
    return null;
  }

  return {
    id: '', // Will be assigned during build
    filename,
    frontmatter: frontmatter as RuleFrontmatter,
    title: frontmatter.title,
    content: bodyContent,
    section,
  };
}

function parseFrontmatter(str: string): Partial<RuleFrontmatter> {
  const result: Record<string, string> = {};

  const lines = str.split('\n');
  for (const line of lines) {
    const match = line.match(/^(\w+):\s*(.+)$/);
    if (match) {
      result[match[1]] = match[2].trim();
    }
  }

  return result as Partial<RuleFrontmatter>;
}

export function parseSectionsFile(filepath: string): Section[] {
  const content = readFileSync(filepath, 'utf-8');
  const sections: Section[] = [];

  // Match section headers like "## 1. Database Optimization (db)"
  const sectionRegex = /## (\d+)\. ([^(]+) \((\w+)\)\n\n\*\*Impact:\*\* (\w+(?:-\w+)?)\n\*\*Description:\*\* ([^\n]+)/g;

  let match;
  while ((match = sectionRegex.exec(content)) !== null) {
    sections.push({
      number: parseInt(match[1], 10),
      title: match[2].trim(),
      prefix: match[3],
      impact: match[4],
      description: match[5],
    });
  }

  return sections;
}
