import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";

export function ThemeToggle() {
  const { resolvedTheme, setTheme, theme } = useTheme();

  const cycleTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const themeLabel = {
    light: "Switch to dark mode",
    dark: "Switch to system theme",
    system: "Switch to light mode",
  }[theme];

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={cycleTheme}
      aria-label={themeLabel}
      title={`Current: ${theme} mode`}
    >
      {resolvedTheme === "dark" ? (
        <Moon className="size-5" aria-hidden="true" />
      ) : (
        <Sun className="size-5" aria-hidden="true" />
      )}
      <span className="sr-only">{themeLabel}</span>
    </Button>
  );
}
