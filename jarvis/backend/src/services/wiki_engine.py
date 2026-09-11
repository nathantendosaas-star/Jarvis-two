"""Stateful LLM Wiki Engine — Maintains agency compounding knowledge files (clients.md, campaigns.md, agency_playbook.md, leads.md, seo_research.md)."""

from pathlib import Path
from typing import Dict, Any

WIKI_DIR = Path(__file__).resolve().parent.parent.parent.parent / "Cached" / "wiki"


def update_wiki_page(page_name: str, content: str, mode: str = "append") -> Dict[str, Any]:
    """Create or update stateful agency wiki markdown documents."""
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    if not page_name.endswith(".md"):
        page_name = f"{page_name}.md"

    page_path = WIKI_DIR / page_name
    if mode == "append" and page_path.exists():
        existing = page_path.read_text(encoding="utf-8")
        updated = existing + "\n\n" + content
    else:
        updated = content

    page_path.write_text(updated, encoding="utf-8")
    return {"success": True, "page": page_name, "path": str(page_path)}


def read_wiki_page(page_name: str) -> str:
    """Read contents of an agency wiki document."""
    if not page_name.endswith(".md"):
        page_name = f"{page_name}.md"
    page_path = WIKI_DIR / page_name
    if not page_path.exists():
        return ""
    return page_path.read_text(encoding="utf-8")
