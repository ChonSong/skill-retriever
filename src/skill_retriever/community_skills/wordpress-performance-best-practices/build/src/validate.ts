import { readdirSync, readFileSync } from 'fs';
import { join } from 'path';
import { config, sectionPrefixes } from './config.js';
import { parseRuleFile } from './parser.js';

interface ValidationError {
  file: string;
  error: string;
}

function validate(): boolean {
  console.log('Validating WordPress Performance Best Practices rules...\n');

  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  // Load all rule files
  const files = readdirSync(config.rulesDir)
    .filter(f => f.endsWith('.md') && !f.startsWith('_'));

  console.log(`Checking ${files.length} rule files...\n`);

  const validImpacts = ['CRITICAL', 'HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'LOW-MEDIUM', 'LOW'];

  for (const file of files) {
    const filepath = join(config.rulesDir, file);
    const content = readFileSync(filepath, 'utf-8');

    // Check frontmatter exists
    if (!content.startsWith('---')) {
      errors.push({ file, error: 'Missing frontmatter' });
      continue;
    }

    // Parse rule
    const rule = parseRuleFile(filepath, file);

    if (!rule) {
      errors.push({ file, error: 'Failed to parse rule' });
      continue;
    }

    // Validate title
    if (!rule.frontmatter.title) {
      errors.push({ file, error: 'Missing title in frontmatter' });
    }

    // Validate impact
    if (!rule.frontmatter.impact) {
      errors.push({ file, error: 'Missing impact in frontmatter' });
    } else if (!validImpacts.includes(rule.frontmatter.impact)) {
      errors.push({ file, error: `Invalid impact level: ${rule.frontmatter.impact}` });
    }

    // Validate tags
    if (!rule.frontmatter.tags) {
      warnings.push({ file, error: 'Missing tags in frontmatter' });
    }

    // Check for code examples
    const hasIncorrect = content.includes('**Incorrect');
    const hasCorrect = content.includes('**Correct');

    if (!hasIncorrect) {
      errors.push({ file, error: 'Missing "Incorrect" code example' });
    }

    if (!hasCorrect) {
      errors.push({ file, error: 'Missing "Correct" code example' });
    }

    // Check for code blocks
    const codeBlocks = content.match(/```[\w]*/g) || [];
    if (codeBlocks.length < 2) {
      warnings.push({ file, error: 'Expected at least 2 code blocks' });
    }

    // Check filename matches section prefix
    const prefix = file.split('-')[0];
    if (!sectionPrefixes[prefix]) {
      errors.push({ file, error: `Unknown section prefix: ${prefix}` });
    }
  }

  // Report results
  if (errors.length > 0) {
    console.log('ERRORS:');
    for (const { file, error } of errors) {
      console.log(`  ✗ ${file}: ${error}`);
    }
    console.log();
  }

  if (warnings.length > 0) {
    console.log('WARNINGS:');
    for (const { file, error } of warnings) {
      console.log(`  ⚠ ${file}: ${error}`);
    }
    console.log();
  }

  const passed = files.length - errors.length;
  console.log(`\nValidation complete: ${passed}/${files.length} files passed`);

  if (errors.length > 0) {
    console.log('\n❌ Validation failed');
    return false;
  }

  console.log('\n✓ All validations passed');
  return true;
}

// Run validation
const success = validate();
process.exit(success ? 0 : 1);
