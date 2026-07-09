import { createFileRoute, Link } from "@tanstack/react-router";
import { conceptsList } from "@/content/generated";
import { Lightbulb, Layers, Shield, Boxes } from "lucide-react";

export const Route = createFileRoute("/concepts/")({
  component: ConceptsIndex,
});

const categoryIcons: Record<string, typeof Lightbulb> = {
  core: Boxes,
  security: Shield,
  architecture: Layers,
  general: Lightbulb,
};

const categoryDescriptions: Record<string, string> = {
  core: "Fundamental building blocks of NestJS applications",
  security: "Authentication, authorization, and protection patterns",
  architecture: "Structural patterns and organization principles",
  general: "General concepts and utilities",
};

function ConceptsIndex() {
  // Group concepts by category
  const categories = conceptsList.reduce(
    (acc, concept) => {
      const cat = concept.category || "general";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(concept);
      return acc;
    },
    {} as Record<string, typeof conceptsList>
  );

  const categoryOrder = ["core", "security", "architecture", "general"];

  const sortedCategories = Object.entries(categories).sort(
    ([a], [b]) => categoryOrder.indexOf(a) - categoryOrder.indexOf(b)
  );

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Concepts
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Understand the core concepts that power NestJS applications. These
          explanations help you grasp the "why" behind the patterns.
        </p>
      </header>

      <div className="space-y-12">
        {sortedCategories.map(([category, concepts]) => {
          const Icon = categoryIcons[category] || Lightbulb;
          const description = categoryDescriptions[category];
          return (
            <section key={category} className="space-y-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Icon className="size-5 text-muted-foreground" />
                  <h2 className="text-xl font-semibold capitalize">
                    {category}
                  </h2>
                </div>
                {description && (
                  <p className="text-sm text-muted-foreground">{description}</p>
                )}
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {concepts.map((concept) => (
                  <Link
                    key={concept.slug}
                    to="/concepts/$slug"
                    params={{ slug: concept.slug }}
                    className="group rounded-lg border border-border bg-card p-5 transition-colors hover:border-foreground/20 hover:bg-accent/50"
                  >
                    <div className="space-y-2">
                      <h3 className="font-semibold group-hover:text-primary">
                        {concept.title}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {concept.description}
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
