#!/usr/bin/env python3
"""Archive org-prefixed duplicate skills, keeping the canonical version.

Strategy:
- For each `sickn33-X` / `affaan-m-X` skill:
  - If `X` also exists as a standalone skill → archive the prefixed version (duplicate)
  - If `X` does NOT exist → rename prefixed to canonical (it's the only copy)
- Dry-run by default. Use `--execute` to actually move/rename.
"""
import os
import shutil
from pathlib import Path
from collections import Counter

SKILLS_DIR = Path.home() / ".hermes" / "skills"
ARCHIVE_DIR = SKILLS_DIR / "_archived"
ORG_PREFIXES = ("sickn33-", "affaan-m-")


def find_org_prefixed():
    """Find all org-prefixed skill directories."""
    prefixed = []
    for name in os.listdir(SKILLS_DIR):
        if any(name.startswith(p) for p in ORG_PREFIXES):
            prefixed.append(name)
    return sorted(prefixed)


def strip_prefix(name):
    """Strip org prefix to get canonical name."""
    for prefix in ORG_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


class DedupExecutor:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.archived = 0
        self.renamed = 0
        self.errors = 0

    def archive(self, src_name, reason):
        """Move a skill to _archived/."""
        src = SKILLS_DIR / src_name
        dst = ARCHIVE_DIR / src_name
        if self.dry_run:
            print(f"  [DRY-RUN] Archive {src_name} ({reason})")
        else:
            try:
                ARCHIVE_DIR.mkdir(exist_ok=True)
                shutil.move(str(src), str(dst))
                print(f"  Archived {src_name} ({reason})")
            except Exception as e:
                print(f"  ERROR archiving {src_name}: {e}")
                self.errors += 1
        self.archived += 1

    def rename(self, src_name, dst_name):
        """Rename a skill to its canonical name."""
        src = SKILLS_DIR / src_name
        dst = SKILLS_DIR / dst_name
        if self.dry_run:
            print(f"  [DRY-RUN] Rename {src_name} → {dst_name}")
        else:
            try:
                if dst.exists():
                    # Canonical exists, archive the prefixed instead
                    self.archive(src_name, "canonical exists")
                    return
                shutil.move(str(src), str(dst))
                print(f"  Renamed {src_name} → {dst_name}")
            except Exception as e:
                print(f"  ERROR renaming {src_name}: {e}")
                self.errors += 1
        self.renamed += 1

    def summary(self):
        print(f"\nSummary: {self.archived} archived, {self.renamed} renamed, {self.errors} errors")


def main(dry_run=True):
    prefixed_names = find_org_prefixed()
    print(f"Found {len(prefixed_names)} org-prefixed skills in {SKILLS_DIR}\n")

    exe = DedupExecutor(dry_run)

    for name in prefixed_names:
        canonical = strip_prefix(name)
        canonical_path = SKILLS_DIR / canonical
        if canonical_path.exists():
            exe.archive(name, f"canonical '{canonical}' exists")
        else:
            exe.rename(name, canonical)

    exe.summary()


if __name__ == "__main__":
    import sys
    dry_run = "--execute" not in sys.argv
    if dry_run:
        print("=== DRY RUN (use --execute to apply) ===\n")
    main(dry_run=dry_run)
