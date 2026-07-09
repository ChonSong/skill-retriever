import { createFileRoute, Link } from "@tanstack/react-router";
import { sections } from "@/content/generated";
import { ArrowRight, Sparkles, BookOpen, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  component: HomePage,
});

const impactColors: Record<string, string> = {
  CRITICAL: "bg-red-500/10 text-red-500 border-red-500/20",
  HIGH: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  "MEDIUM-HIGH": "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  MEDIUM: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  "LOW-MEDIUM": "bg-green-500/10 text-green-500 border-green-500/20",
  LOW: "bg-slate-500/10 text-slate-500 border-slate-500/20",
};

function HomePage() {
  const totalRules = sections.reduce((acc, s) => acc + s.rules.length, 0);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="space-y-6 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5 text-sm text-muted-foreground">
          <Sparkles className="size-4 text-nestjs" />
          Skills aren't only for AI
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          NestJS Best Practices
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          A comprehensive guide to building production-ready NestJS applications.{" "}
          <span className="text-foreground font-medium">{totalRules} rules</span> across{" "}
          <span className="text-foreground font-medium">{sections.length} categories</span>,
          optimized for humans and AI agents alike.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Button asChild size="lg">
            <Link to="/rules/$slug" params={{ slug: sections[0]?.rules[0]?.slug ?? "" }}>
              <BookOpen className="size-4" />
              Start Reading
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a
              href="https://github.com/kadajett/agent-nestjs-skills"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </Button>
        </div>
      </section>

      {/* Stats */}
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          <div className="text-3xl font-bold text-nestjs">{totalRules}</div>
          <div className="text-sm text-muted-foreground">Best Practice Rules</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          <div className="text-3xl font-bold text-nestjs">{sections.length}</div>
          <div className="text-sm text-muted-foreground">Categories</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          <div className="flex items-center justify-center gap-1 text-3xl font-bold text-nestjs">
            <Zap className="size-6" />
          </div>
          <div className="text-sm text-muted-foreground">AI-Optimized</div>
        </div>
      </section>

      {/* Sections Grid */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold">Categories</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {sections.map((section) => (
            <Link
              key={section.id}
              to="/rules/$slug"
              params={{ slug: section.rules[0]?.slug ?? "" }}
              className="group rounded-lg border border-border bg-card p-6 transition-colors hover:border-nestjs/50 hover:bg-accent"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-muted-foreground">
                      {section.order}.
                    </span>
                    <h3 className="font-semibold">{section.title}</h3>
                  </div>
                  <span
                    className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${impactColors[section.impact] ?? impactColors.MEDIUM}`}
                  >
                    {section.impact}
                  </span>
                </div>
                <ArrowRight className="size-5 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-nestjs" />
              </div>
              <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
                {section.description}
              </p>
              <div className="mt-3 text-xs text-muted-foreground">
                {section.rules.length} rules
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
