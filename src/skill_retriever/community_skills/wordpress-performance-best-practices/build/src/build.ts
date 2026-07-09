import { readdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { config } from './config.js';
import { parseRuleFile, parseSectionsFile } from './parser.js';
import type { Rule, Section, Metadata } from './types.js';

function build() {
  console.log('Building WordPress Performance Best Practices AGENTS.md...\n');

  // Load metadata
  const metadata: Metadata = JSON.parse(readFileSync(config.metadataFile, 'utf-8'));

  // Load sections
  const sectionsFile = join(config.rulesDir, '_sections.md');
  const sections = parseSectionsFile(sectionsFile);
  console.log(`Loaded ${sections.length} sections`);

  // Load all rule files
  const files = readdirSync(config.rulesDir)
    .filter(f => f.endsWith('.md') && !f.startsWith('_'));

  console.log(`Found ${files.length} rule files`);

  // Parse rules
  const rules: Rule[] = [];
  for (const file of files) {
    const filepath = join(config.rulesDir, file);
    const rule = parseRuleFile(filepath, file);
    if (rule) {
      rules.push(rule);
    }
  }

  // Group rules by section
  const rulesBySection = new Map<number, Rule[]>();
  for (const rule of rules) {
    const sectionRules = rulesBySection.get(rule.section) || [];
    sectionRules.push(rule);
    rulesBySection.set(rule.section, sectionRules);
  }

  // Sort rules within each section and assign IDs
  for (const [section, sectionRules] of rulesBySection) {
    sectionRules.sort((a, b) => a.filename.localeCompare(b.filename));
    sectionRules.forEach((rule, index) => {
      rule.id = `${section}.${index + 1}`;
    });
  }

  // Generate output
  let output = generateHeader(metadata);
  output += generateTableOfContents(sections, rulesBySection);
  output += generateSections(sections, rulesBySection);
  output += generateReferences(metadata.references);

  // Write output
  writeFileSync(config.outputFile, output);

  const stats = {
    sections: sections.length,
    rules: rules.length,
    bytes: Buffer.byteLength(output, 'utf-8'),
  };

  console.log(`\nBuild complete!`);
  console.log(`  Sections: ${stats.sections}`);
  console.log(`  Rules: ${stats.rules}`);
  console.log(`  Output size: ${(stats.bytes / 1024).toFixed(1)} KB`);
  console.log(`  Output file: ${config.outputFile}`);
}

function generateHeader(metadata: Metadata): string {
  return `# WordPress Performance Best Practices

**Version ${metadata.version}**
${metadata.organization}
${metadata.date}

> **Note:** This document is designed for AI agents and LLMs assisting with WordPress development. It provides structured performance guidelines with clear examples of incorrect and correct implementations.

## Abstract

${metadata.abstract}

`;
}

function generateTableOfContents(sections: Section[], rulesBySection: Map<number, Rule[]>): string {
  let toc = '## Table of Contents\n\n';

  for (const section of sections) {
    const rules = rulesBySection.get(section.number) || [];
    toc += `### ${section.number}. ${section.title} (${section.impact})\n\n`;

    for (const rule of rules) {
      toc += `- [${rule.id} ${rule.title}](#${rule.id.replace('.', '')}-${slugify(rule.title)})\n`;
    }
    toc += '\n';
  }

  return toc;
}

function generateSections(sections: Section[], rulesBySection: Map<number, Rule[]>): string {
  let content = '';

  for (const section of sections) {
    content += `---\n\n## ${section.number}. ${section.title}\n\n`;
    content += `**Impact Level:** ${section.impact}\n\n`;
    content += `${section.description}\n\n`;

    const rules = rulesBySection.get(section.number) || [];

    for (const rule of rules) {
      content += generateRule(rule);
    }
  }

  return content;
}

function generateRule(rule: Rule): string {
  let content = `### ${rule.id} ${rule.title}\n\n`;

  // Impact line
  const impactDesc = rule.frontmatter.impactDescription
    ? ` (${rule.frontmatter.impactDescription})`
    : '';
  content += `**Impact: ${rule.frontmatter.impact}${impactDesc}**\n\n`;

  // Tags
  if (rule.frontmatter.tags) {
    content += `*Tags: ${rule.frontmatter.tags}*\n\n`;
  }

  // Main content (skip the ## title as we already have it)
  let ruleContent = rule.content;
  // Remove the duplicate title if present
  ruleContent = ruleContent.replace(/^## .+\n+/, '');
  content += ruleContent + '\n\n';

  return content;
}

function generateReferences(references: string[]): string {
  let content = '---\n\n## References\n\n';

  for (const ref of references) {
    content += `- ${ref}\n`;
  }

  return content;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

// Run build
build();
