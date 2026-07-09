import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { rules, sections } from "@/content/generated";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/rules/$slug")({
  component: RulePage,
  loader: ({ params }) => {
    const rule = rules[params.slug];
    if (!rule) {
      throw notFound();
    }
    return rule;
  },
});

const impactColors: Record<string, string> = {
  CRITICAL: "bg-red-500/10 text-red-500 border-red-500/20",
  HIGH: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  "MEDIUM-HIGH": "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  MEDIUM: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  "LOW-MEDIUM": "bg-green-500/10 text-green-500 border-green-500/20",
  LOW: "bg-slate-500/10 text-slate-500 border-slate-500/20",
};

function RulePage() {
  const rule = Route.useLoaderData();

  // Find section and position
  const section = sections.find((s) => s.id === rule.section);
  const allRules = sections.flatMap((s) => s.rules);
  const currentIndex = allRules.findIndex((r) => r.slug === rule.slug);
  const prevRule = currentIndex > 0 ? allRules[currentIndex - 1] : null;
  const nextRule = currentIndex < allRules.length - 1 ? allRules[currentIndex + 1] : null;

  return (
    <article className="space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/" className="hover:text-foreground">
          Home
        </Link>
        <span>/</span>
        <span>{section?.title}</span>
      </div>

      {/* Header */}
      <header className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          {section && (
            <span
              className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${impactColors[section.impact] ?? impactColors.MEDIUM}`}
            >
              {section.impact}
            </span>
          )}
          <span className="text-sm text-muted-foreground">
            {section?.title}
          </span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{rule.title}</h1>
      </header>

      {/* Content */}
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: rule.content }}
      />

      {/* Source link */}
      <div className="border-t border-border pt-6">
        <a
          href={`https://github.com/kadajett/agent-nestjs-skills/blob/main/rules/${rule.filename}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ExternalLink className="size-4" />
          Edit this page on GitHub
        </a>
      </div>

      {/* Navigation */}
      <nav className="flex items-center justify-between border-t border-border pt-6">
        {prevRule ? (
          <Button asChild variant="ghost" className="gap-2">
            <Link to="/rules/$slug" params={{ slug: prevRule.slug }}>
              <ChevronLeft className="size-4" />
              <span className="hidden sm:inline">{prevRule.title}</span>
              <span className="sm:hidden">Previous</span>
            </Link>
          </Button>
        ) : (
          <div />
        )}
        {nextRule ? (
          <Button asChild variant="ghost" className="gap-2">
            <Link to="/rules/$slug" params={{ slug: nextRule.slug }}>
              <span className="hidden sm:inline">{nextRule.title}</span>
              <span className="sm:hidden">Next</span>
              <ChevronRight className="size-4" />
            </Link>
          </Button>
        ) : (
          <div />
        )}
      </nav>
    </article>
  );
}
