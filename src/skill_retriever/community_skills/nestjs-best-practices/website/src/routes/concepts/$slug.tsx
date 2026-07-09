import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { concepts, conceptsList, rules } from "@/content/generated";
import { ChevronLeft, ChevronRight, ExternalLink, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/concepts/$slug")({
  component: ConceptPage,
  loader: ({ params }) => {
    const concept = concepts[params.slug];
    if (!concept) {
      throw notFound();
    }
    return concept;
  },
});

function ConceptPage() {
  const concept = Route.useLoaderData();

  // Find position for prev/next navigation
  const currentIndex = conceptsList.findIndex((c) => c.slug === concept.slug);
  const prevConcept = currentIndex > 0 ? conceptsList[currentIndex - 1] : null;
  const nextConcept =
    currentIndex < conceptsList.length - 1
      ? conceptsList[currentIndex + 1]
      : null;

  // Get related rules
  const relatedRules = concept.relatedRules
    ?.map((slug) => rules[slug])
    .filter(Boolean);

  return (
    <article className="space-y-8">
      {/* Breadcrumb */}
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-2 text-sm text-muted-foreground"
      >
        <Link to="/" className="hover:text-foreground">
          Home
        </Link>
        <span aria-hidden="true">/</span>
        <Link to="/concepts" className="hover:text-foreground">
          Concepts
        </Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{concept.title}</span>
      </nav>

      {/* Header */}
      <header className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium capitalize">
            {concept.category}
          </span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          {concept.title}
        </h1>
        {concept.description && (
          <p className="max-w-2xl text-lg text-muted-foreground">
            {concept.description}
          </p>
        )}
      </header>

      {/* Content */}
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: concept.content }}
      />

      {/* Related Rules */}
      {relatedRules && relatedRules.length > 0 && (
        <aside className="space-y-4 rounded-lg border border-border bg-muted/50 p-6">
          <div className="flex items-center gap-2">
            <BookOpen className="size-5 text-muted-foreground" />
            <h2 className="font-semibold">Related Rules</h2>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {relatedRules.map((rule) => (
              <li key={rule.slug}>
                <Link
                  to="/rules/$slug"
                  params={{ slug: rule.slug }}
                  className="block rounded-md border border-border bg-background p-3 transition-colors hover:border-foreground/20"
                >
                  <span className="font-medium">{rule.title}</span>
                </Link>
              </li>
            ))}
          </ul>
        </aside>
      )}

      {/* Source link */}
      <div className="border-t border-border pt-6">
        <a
          href={`https://github.com/kadajett/agent-nestjs-skills/blob/main/website/content/concepts/${concept.filename}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ExternalLink className="size-4" />
          Edit this page on GitHub
        </a>
      </div>

      {/* Navigation */}
      <nav
        aria-label="Concept navigation"
        className="flex items-center justify-between border-t border-border pt-6"
      >
        {prevConcept ? (
          <Button asChild variant="ghost" className="gap-2">
            <Link to="/concepts/$slug" params={{ slug: prevConcept.slug }}>
              <ChevronLeft className="size-4" aria-hidden="true" />
              <span className="hidden sm:inline">{prevConcept.title}</span>
              <span className="sm:hidden">Previous</span>
            </Link>
          </Button>
        ) : (
          <div />
        )}
        {nextConcept ? (
          <Button asChild variant="ghost" className="gap-2">
            <Link to="/concepts/$slug" params={{ slug: nextConcept.slug }}>
              <span className="hidden sm:inline">{nextConcept.title}</span>
              <span className="sm:hidden">Next</span>
              <ChevronRight className="size-4" aria-hidden="true" />
            </Link>
          </Button>
        ) : (
          <div />
        )}
      </nav>
    </article>
  );
}
