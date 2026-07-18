#!/usr/bin/env python3
"""Extract version from CLAUDE.md and update template.html and analyze-game.py.

Usage:
    python3 tools/update-version.py

This script reads CLAUDE.md to find the current version (e.g., "**Version 6**")
and updates all references in:
  - template.html (HTML version display and GAME data field)
  - analyze-game.py (analysisNote version reference)

Run this whenever the version in CLAUDE.md is updated, or add it as a pre-commit hook.
"""

import re
from pathlib import Path

def extract_version_from_claude_md():
    """Extract version number from CLAUDE.md (e.g., '**Version 6**' -> 6)."""
    claude_md = Path(__file__).parent.parent / "CLAUDE.md"
    with open(claude_md) as f:
        first_content = f.read(200)  # Read first 200 chars to find version

    match = re.search(r'\*\*Version\s+(\d+)\*\*', first_content)
    if match:
        return int(match.group(1))
    raise ValueError("Could not find version in CLAUDE.md (expecting '**Version N**')")

def update_template_html(version):
    """Update Version display in template.html."""
    template_path = Path(__file__).parent.parent / "template.html"
    content = template_path.read_text()

    # Update HTML version display
    content = re.sub(
        r'<span style="color:var\(--muted;\);">Version&nbsp;\d+</span>',
        f'<span style="color:var(--muted);">Version&nbsp;{version}</span>',
        content
    )

    # Update GAME data version field
    content = re.sub(
        r'version:\s*"version\s+\d+"',
        f'version: "version {version}"',
        content
    )

    template_path.write_text(content)
    print(f"✓ Updated template.html to Version {version}")

def update_game_files(version):
    """Update Version display and GAME data in all game files."""
    games_dir = Path(__file__).parent.parent / "games"
    html_files = list(games_dir.glob("202*-*.html"))

    updated_count = 0
    for html_file in html_files:
        content = html_file.read_text()
        original = content

        # Update HTML version display
        content = re.sub(
            r'<span style="color:var\(--muted;\);">Version&nbsp;\d+</span>',
            f'<span style="color:var(--muted);">Version&nbsp;{version}</span>',
            content
        )

        # Update GAME data version field (both JSON-quoted and unquoted)
        content = re.sub(
            r'"version":\s*"version\s+\d+"',
            f'"version": "version {version}"',
            content
        )
        content = re.sub(
            r'version:\s*"version\s+\d+"',
            f'version: "version {version}"',
            content
        )

        if content != original:
            html_file.write_text(content)
            updated_count += 1

    if updated_count > 0:
        print(f"✓ Updated {updated_count} game file(s) to Version {version}")

if __name__ == "__main__":
    version = extract_version_from_claude_md()
    print(f"Found Version {version} in CLAUDE.md")
    update_template_html(version)
    update_game_files(version)
    print(f"\nAll files updated to Version {version}")
