import { Link, useLocation } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import { ChevronRight, BookOpen, Lightbulb, FileText } from "lucide-react";
import { useState } from "react";
import {
  sections,
  guidesList,
  conceptsList,
  type Section,
  type Rule,
} from "@/content/generated";

interface NavSectionProps {
  section: Section;
  isActive: boolean;
}

function NavSection({ section, isActive }: NavSectionProps) {
  const [isOpen, setIsOpen] = useState(isActive);
  const location = useLocation();

  return (
    <div className="mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          isActive && "text-nestjs"
        )}
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2">
          <span className="text-xs font-bold text-muted-foreground">
            {section.order}.
          </span>
          {section.title}
        </span>
        <ChevronRight
          className={cn(
            "size-4 text-muted-foreground transition-transform",
            isOpen && "rotate-90"
          )}
          aria-hidden="true"
        />
      </button>
      {isOpen && (
        <div className="ml-4 mt-1 space-y-1 border-l border-border pl-3">
          {section.rules.map((rule: Rule) => {
            const isRuleActive = location.pathname.includes(rule.slug);
            return (
              <Link
                key={rule.slug}
                to="/rules/$slug"
                params={{ slug: rule.slug }}
                className={cn(
                  "block rounded-md px-3 py-1.5 text-sm transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  isRuleActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground"
                )}
                aria-current={isRuleActive ? "page" : undefined}
              >
                {rule.title}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface CollapsibleNavProps {
  title: string;
  icon: React.ReactNode;
  items: Array<{ slug: string; title: string }>;
  basePath: string;
  defaultOpen?: boolean;
}

function CollapsibleNav({
  title,
  icon,
  items,
  basePath,
  defaultOpen = false,
}: CollapsibleNavProps) {
  const location = useLocation();
  const isActive = location.pathname.startsWith(basePath);
  const [isOpen, setIsOpen] = useState(defaultOpen || isActive);

  return (
    <div className="mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
          "hover:bg-accent hover:text-accent-foreground",
          isActive && "text-nestjs"
        )}
        aria-expanded={isOpen}
      >
        <span className="flex items-center gap-2">
          {icon}
          {title}
        </span>
        <ChevronRight
          className={cn(
            "size-4 text-muted-foreground transition-transform",
            isOpen && "rotate-90"
          )}
          aria-hidden="true"
        />
      </button>
      {isOpen && (
        <div className="ml-4 mt-1 space-y-1 border-l border-border pl-3">
          {items.map((item) => {
            const itemPath = `${basePath}/${item.slug}`;
            const isItemActive = location.pathname === itemPath;
            return (
              <Link
                key={item.slug}
                to={itemPath}
                className={cn(
                  "block rounded-md px-3 py-1.5 text-sm transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  isItemActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground"
                )}
                aria-current={isItemActive ? "page" : undefined}
              >
                {item.title}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="space-y-6" aria-label="Main navigation">
      {/* Getting Started Section */}
      <div className="space-y-1">
        <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Learn
        </h3>
        <CollapsibleNav
          title="Guides"
          icon={<BookOpen className="size-4" aria-hidden="true" />}
          items={guidesList.map((g) => ({ slug: g.slug, title: g.title }))}
          basePath="/guides"
          defaultOpen
        />
        <CollapsibleNav
          title="Concepts"
          icon={<Lightbulb className="size-4" aria-hidden="true" />}
          items={conceptsList.map((c) => ({ slug: c.slug, title: c.title }))}
          basePath="/concepts"
        />
      </div>

      {/* Rules Section */}
      <div className="space-y-1">
        <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Rules Reference
        </h3>
        {sections.map((section) => {
          const isActive = section.rules.some((rule: Rule) =>
            location.pathname.includes(rule.slug)
          );
          return (
            <NavSection
              key={section.id}
              section={section}
              isActive={isActive}
            />
          );
        })}
      </div>
    </nav>
  );
}
