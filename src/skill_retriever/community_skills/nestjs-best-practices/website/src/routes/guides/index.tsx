import { createFileRoute, Link } from "@tanstack/react-router";
import { guidesList } from "@/content/generated";
import { BookOpen, Clock, GraduationCap } from "lucide-react";

export const Route = createFileRoute("/guides/")({
  component: GuidesIndex,
});

const difficultyColors: Record<string, string> = {
  beginner: "bg-green-500/10 text-green-500 border-green-500/20",
  intermediate: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  advanced: "bg-red-500/10 text-red-500 border-red-500/20",
};

const categoryIcons: Record<string, typeof BookOpen> = {
  "getting-started": GraduationCap,
  architecture: BookOpen,
  patterns: BookOpen,
  "error-handling": BookOpen,
  security: BookOpen,
};

function GuidesIndex() {
  // Group guides by category
  const categories = guidesList.reduce(
    (acc, guide) => {
      const cat = guide.category || "general";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(guide);
      return acc;
    },
    {} as Record<string, typeof guidesList>
  );

  const categoryOrder = [
    "getting-started",
    "architecture",
    "patterns",
    "error-handling",
    "security",
    "general",
  ];

  const sortedCategories = Object.entries(categories).sort(
    ([a], [b]) => categoryOrder.indexOf(a) - categoryOrder.indexOf(b)
  );

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Guides
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Step-by-step tutorials to help you build production-ready NestJS
          applications. Start with the basics and work your way up.
        </p>
      </header>

      <div className="space-y-12">
        {sortedCategories.map(([category, guides]) => {
          const Icon = categoryIcons[category] || BookOpen;
          return (
            <section key={category} className="space-y-4">
              <div className="flex items-center gap-2">
                <Icon className="size-5 text-muted-foreground" />
                <h2 className="text-xl font-semibold capitalize">
                  {category.replace(/-/g, " ")}
                </h2>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {guides.map((guide) => (
                  <Link
                    key={guide.slug}
                    to="/guides/$slug"
                    params={{ slug: guide.slug }}
                    className="group rounded-lg border border-border bg-card p-5 transition-colors hover:border-foreground/20 hover:bg-accent/50"
                  >
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-xs font-medium ${difficultyColors[guide.difficulty] ?? difficultyColors.beginner}`}
                        >
                          {guide.difficulty}
                        </span>
                        {guide.estimatedTime && (
                          <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="size-3" />
                            {guide.estimatedTime}
                          </span>
                        )}
                      </div>
                      <h3 className="font-semibold group-hover:text-primary">
                        {guide.title}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {guide.description}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
