import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import matter from "gray-matter";
import { marked, type Tokens } from "marked";
import { createHighlighter, type Highlighter } from "shiki";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BASE_PATH = "/agent-nestjs-skills";
const RULES_DIR = path.resolve(__dirname, "../../rules");
const CONTENT_DIR = path.resolve(__dirname, "../content");
const OUTPUT_FILE = path.resolve(__dirname, "../src/content/generated.ts");

interface SectionMeta {
  order: number;
  id: string;
  title: string;
  impact: string;
  description: string;
}

interface RuleMeta {
  slug: string;
  filename: string;
  title: string;
  impact: string;
  impactDescription: string;
  tags: string[];
  section: string;
  content: string;
}

interface GuideMeta {
  slug: string;
  filename: string;
  title: string;
  description: string;
  order: number;
  category: string;
  difficulty: string;
  estimatedTime: string;
  prerequisites: string[];
  content: string;
}

interface ConceptMeta {
  slug: string;
  filename: string;
  title: string;
  description: string;
  order: number;
  category: string;
  relatedRules: string[];
  content: string;
}

let highlighter: Highlighter | null = null;

async function getHighlighter(): Promise<Highlighter> {
  if (!highlighter) {
    highlighter = await createHighlighter({
      themes: ["github-dark", "github-light"],
      langs: ["typescript", "javascript", "bash", "json", "yaml", "sql", "html", "css", "plaintext"],
    });
  }
  return highlighter;
}

function createMarkedRenderer(hl: Highlighter): marked.Renderer {
  const renderer = new marked.Renderer();

  renderer.code = function (this: marked.Renderer, token: Tokens.Code): string {
    const { text, lang } = token;
    const language = lang || "plaintext";

    // Map common language aliases
    const langMap: Record<string, string> = {
      ts: "typescript",
      js: "javascript",
      sh: "bash",
      shell: "bash",
      yml: "yaml",
    };
    const normalizedLang = langMap[language] || language;

    // Check if language is supported, fallback to plaintext
    const supportedLangs = hl.getLoadedLanguages();
    const finalLang = supportedLangs.includes(normalizedLang) ? normalizedLang : "plaintext";

    try {
      const highlighted = hl.codeToHtml(text, {
        lang: finalLang,
        themes: {
          light: "github-light",
          dark: "github-dark",
        },
      });

      // Wrap in a container with language label
      return `<div class="code-block" data-language="${language}">
        <div class="code-block-header">
          <span class="code-block-lang">${language}</span>
        </div>
        ${highlighted}
      </div>`;
    } catch {
      // Fallback to plain code block if highlighting fails
      const escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return `<pre><code class="language-${language}">${escaped}</code></pre>`;
    }
  };

  // Rewrite internal links to include base path
  renderer.link = function (this: marked.Renderer, token: Tokens.Link): string {
    const href = token.href || "";
    const title = token.title ? ` title="${token.title}"` : "";
    const text = this.parser?.parseInline(token.tokens) || token.text;

    // Check if it's an internal link (starts with /)
    let finalHref = href;
    if (href.startsWith("/") && !href.startsWith("//")) {
      finalHref = `${BASE_PATH}${href}`;
    }

    // External links open in new tab
    if (href.startsWith("http://") || href.startsWith("https://")) {
      return `<a href="${finalHref}"${title} target="_blank" rel="noopener noreferrer">${text}</a>`;
    }

    return `<a href="${finalHref}"${title}>${text}</a>`;
  };

  // Improve table rendering
  renderer.table = function (this: marked.Renderer, token: Tokens.Table): string {
    const headers = token.header
      .map((cell) => {
        const content = this.parser?.parseInline(cell.tokens) || cell.text;
        return `<th>${content}</th>`;
      })
      .join("");

    const rows = token.rows
      .map((row) => {
        const cells = row
          .map((cell) => {
            const content = this.parser?.parseInline(cell.tokens) || cell.text;
            return `<td>${content}</td>`;
          })
          .join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");

    return `<div class="table-wrapper">
      <table>
        <thead><tr>${headers}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  };

  return renderer;
}

function parseSections(): SectionMeta[] {
  const sectionsPath = path.join(RULES_DIR, "_sections.md");
  const content = fs.readFileSync(sectionsPath, "utf-8");

  const sections: SectionMeta[] = [];
  const lines = content.split("\n");

  let currentSection: Partial<SectionMeta> | null = null;

  for (const line of lines) {
    const headerMatch = line.match(/^## (\d+)\. ([^(]+)\s*\((\w+)\)/);
    if (headerMatch) {
      if (currentSection && currentSection.id) {
        sections.push(currentSection as SectionMeta);
      }
      currentSection = {
        order: parseInt(headerMatch[1], 10),
        title: headerMatch[2].trim(),
        id: headerMatch[3],
        impact: "",
        description: "",
      };
      continue;
    }

    if (currentSection) {
      const impactMatch = line.match(/^\*\*Impact:\*\*\s*(.+)/);
      if (impactMatch) {
        currentSection.impact = impactMatch[1].trim();
        continue;
      }

      const descMatch = line.match(/^\*\*Description:\*\*\s*(.+)/);
      if (descMatch) {
        currentSection.description = descMatch[1].trim();
        continue;
      }
    }
  }

  if (currentSection && currentSection.id) {
    sections.push(currentSection as SectionMeta);
  }

  return sections;
}

async function parseRules(sections: SectionMeta[]): Promise<RuleMeta[]> {
  const hl = await getHighlighter();
  const renderer = createMarkedRenderer(hl);

  const files = fs.readdirSync(RULES_DIR).filter((f) => {
    return f.endsWith(".md") && !f.startsWith("_");
  });

  const rules: RuleMeta[] = [];

  for (const filename of files) {
    const filePath = path.join(RULES_DIR, filename);
    const fileContent = fs.readFileSync(filePath, "utf-8");
    const { data, content } = matter(fileContent);

    const prefix = filename.split("-")[0];
    const section = sections.find((s) => s.id === prefix);

    if (!section) {
      console.warn(`Warning: No section found for rule ${filename} (prefix: ${prefix})`);
      continue;
    }

    const htmlContent = marked.parse(content, { renderer }) as string;
    const slug = filename.replace(/\.md$/, "");

    rules.push({
      slug,
      filename,
      title: data.title || slug,
      impact: data.impact || section.impact,
      impactDescription: data.impactDescription || "",
      tags: data.tags ? data.tags.split(",").map((t: string) => t.trim()) : [],
      section: section.id,
      content: htmlContent,
    });
  }

  return rules;
}

async function parseGuides(): Promise<GuideMeta[]> {
  const guidesDir = path.join(CONTENT_DIR, "guides");

  if (!fs.existsSync(guidesDir)) {
    return [];
  }

  const hl = await getHighlighter();
  const renderer = createMarkedRenderer(hl);

  const files = fs.readdirSync(guidesDir).filter((f) => f.endsWith(".md"));
  const guides: GuideMeta[] = [];

  for (const filename of files) {
    const filePath = path.join(guidesDir, filename);
    const fileContent = fs.readFileSync(filePath, "utf-8");
    const { data, content } = matter(fileContent);

    const htmlContent = marked.parse(content, { renderer }) as string;
    const slug = filename.replace(/\.md$/, "");

    guides.push({
      slug,
      filename,
      title: data.title || slug,
      description: data.description || "",
      order: data.order || 999,
      category: data.category || "general",
      difficulty: data.difficulty || "beginner",
      estimatedTime: data.estimatedTime || "",
      prerequisites: data.prerequisites || [],
      content: htmlContent,
    });
  }

  return guides.sort((a, b) => a.order - b.order);
}

async function parseConcepts(): Promise<ConceptMeta[]> {
  const conceptsDir = path.join(CONTENT_DIR, "concepts");

  if (!fs.existsSync(conceptsDir)) {
    return [];
  }

  const hl = await getHighlighter();
  const renderer = createMarkedRenderer(hl);

  const files = fs.readdirSync(conceptsDir).filter((f) => f.endsWith(".md"));
  const concepts: ConceptMeta[] = [];

  for (const filename of files) {
    const filePath = path.join(conceptsDir, filename);
    const fileContent = fs.readFileSync(filePath, "utf-8");
    const { data, content } = matter(fileContent);

    const htmlContent = marked.parse(content, { renderer }) as string;
    const slug = filename.replace(/\.md$/, "");

    concepts.push({
      slug,
      filename,
      title: data.title || slug,
      description: data.description || "",
      order: data.order || 999,
      category: data.category || "general",
      relatedRules: data.relatedRules || [],
      content: htmlContent,
    });
  }

  return concepts.sort((a, b) => a.order - b.order);
}

function generateOutput(
  sections: SectionMeta[],
  rules: RuleMeta[],
  guides: GuideMeta[],
  concepts: ConceptMeta[]
): void {
  const rulesBySection = new Map<string, RuleMeta[]>();
  for (const rule of rules) {
    const existing = rulesBySection.get(rule.section) || [];
    existing.push(rule);
    rulesBySection.set(rule.section, existing);
  }

  for (const [, sectionRules] of rulesBySection) {
    sectionRules.sort((a, b) => a.title.localeCompare(b.title));
  }

  const sectionsWithRules = sections
    .sort((a, b) => a.order - b.order)
    .map((section) => ({
      ...section,
      rules: (rulesBySection.get(section.id) || []).map(({ slug, title }) => ({
        slug,
        title,
      })),
    }));

  const rulesLookup = Object.fromEntries(rules.map((r) => [r.slug, r]));
  const guidesLookup = Object.fromEntries(guides.map((g) => [g.slug, g]));
  const conceptsLookup = Object.fromEntries(concepts.map((c) => [c.slug, c]));

  const output = `// Auto-generated by scripts/generate-content.ts
// Do not edit manually

export interface Rule {
  slug: string;
  title: string;
}

export interface Section {
  order: number;
  id: string;
  title: string;
  impact: string;
  description: string;
  rules: Rule[];
}

export interface RuleDetail {
  slug: string;
  filename: string;
  title: string;
  impact: string;
  impactDescription: string;
  tags: string[];
  section: string;
  content: string;
}

export interface GuideDetail {
  slug: string;
  filename: string;
  title: string;
  description: string;
  order: number;
  category: string;
  difficulty: string;
  estimatedTime: string;
  prerequisites: string[];
  content: string;
}

export interface ConceptDetail {
  slug: string;
  filename: string;
  title: string;
  description: string;
  order: number;
  category: string;
  relatedRules: string[];
  content: string;
}

export const sections: Section[] = ${JSON.stringify(sectionsWithRules, null, 2)};

export const rules: Record<string, RuleDetail> = ${JSON.stringify(rulesLookup, null, 2)};

export const guides: Record<string, GuideDetail> = ${JSON.stringify(guidesLookup, null, 2)};

export const guidesList: Array<{ slug: string; title: string; description: string; order: number; category: string; difficulty: string; estimatedTime: string }> = ${JSON.stringify(
    guides.map(({ slug, title, description, order, category, difficulty, estimatedTime }) => ({
      slug,
      title,
      description,
      order,
      category,
      difficulty,
      estimatedTime,
    })),
    null,
    2
  )};

export const concepts: Record<string, ConceptDetail> = ${JSON.stringify(conceptsLookup, null, 2)};

export const conceptsList: Array<{ slug: string; title: string; description: string; order: number; category: string }> = ${JSON.stringify(
    concepts.map(({ slug, title, description, order, category }) => ({
      slug,
      title,
      description,
      order,
      category,
    })),
    null,
    2
  )};
`;

  const outputDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  fs.writeFileSync(OUTPUT_FILE, output, "utf-8");
  console.log(`Generated ${OUTPUT_FILE}`);
  console.log(`  - ${sections.length} sections`);
  console.log(`  - ${rules.length} rules`);
  console.log(`  - ${guides.length} guides`);
  console.log(`  - ${concepts.length} concepts`);
}

async function main() {
  console.log("Generating content from rules and docs...");
  const sections = parseSections();
  const rules = await parseRules(sections);
  const guides = await parseGuides();
  const concepts = await parseConcepts();
  generateOutput(sections, rules, guides, concepts);
}

main().catch(console.error);
