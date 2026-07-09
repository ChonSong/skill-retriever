export interface RuleFrontmatter {
  title: string;
  impact: 'CRITICAL' | 'HIGH' | 'MEDIUM-HIGH' | 'MEDIUM' | 'LOW-MEDIUM' | 'LOW';
  impactDescription?: string;
  tags: string;
}

export interface Rule {
  id: string;
  filename: string;
  frontmatter: RuleFrontmatter;
  title: string;
  content: string;
  section: number;
}

export interface Section {
  number: number;
  prefix: string;
  title: string;
  impact: string;
  description: string;
}

export interface Metadata {
  version: string;
  organization: string;
  date: string;
  abstract: string;
  references: string[];
}

export interface BuildConfig {
  rulesDir: string;
  outputFile: string;
  metadataFile: string;
}
