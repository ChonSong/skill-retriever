import { Link } from "@tanstack/react-router";
import { ThemeToggle } from "./theme-toggle";
import { Navigation } from "./navigation";
import { Github, Menu, X } from "lucide-react";
import { Button } from "./ui/button";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      {/* Skip to main content link for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-nestjs focus:px-4 focus:py-2 focus:text-white focus:outline-none"
      >
        Skip to main content
      </a>

      {/* Header */}
      <header
        className="z-50 shrink-0 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
        role="banner"
      >
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label={sidebarOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={sidebarOpen}
              aria-controls="sidebar-nav"
            >
              {sidebarOpen ? (
                <X className="size-5" aria-hidden="true" />
              ) : (
                <Menu className="size-5" aria-hidden="true" />
              )}
            </Button>
            <Link to="/" className="flex items-center gap-2" aria-label="NestJS Best Practices - Home">
              <div className="flex size-8 items-center justify-center rounded-md bg-nestjs" aria-hidden="true">
                <span className="text-sm font-bold text-white">N</span>
              </div>
              <span className="hidden font-semibold sm:inline">NestJS Best Practices</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/kadajett/agent-nestjs-skills"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground"
              aria-label="View source on GitHub (opens in new tab)"
            >
              <Github className="size-5" aria-hidden="true" />
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main layout below header */}
      <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1">
        {/* Sidebar - independent scroll */}
        <aside
          id="sidebar-nav"
          className={cn(
            "fixed inset-y-0 left-0 z-40 mt-14 w-72 transform overflow-y-auto border-r border-border bg-background px-4 py-6 transition-transform lg:static lg:mt-0 lg:block lg:shrink-0 lg:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
          aria-label="Site navigation"
          role="navigation"
        >
          <Navigation />
        </aside>

        {/* Overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Main content - independent scroll */}
        <main
          id="main-content"
          className="min-w-0 flex-1 overflow-y-auto px-4 py-8 lg:px-8"
          role="main"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
