import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import type { BuildConfig } from './types.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export const config: BuildConfig = {
  rulesDir: join(__dirname, '../../rules'),
  outputFile: join(__dirname, '../../AGENTS.md'),
  metadataFile: join(__dirname, '../../metadata.json'),
};

export const sectionPrefixes: Record<string, number> = {
  'db': 1,
  'cache': 2,
  'asset': 3,
  'theme': 4,
  'plugin': 5,
  'media': 6,
  'api': 7,
  'advanced': 8,
};
