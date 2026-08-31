import re
from pathlib import Path

MARKDOWN_LINK = re.compile(r"\[[^]]+\]\((?!https?://|#)([^)]+)\)")


def test_local_documentation_links_resolve() -> None:
    """Renaming or omitting a linked reviewer artifact must break repository validation."""
    broken: list[str] = []
    for document in Path(".").glob("**/*.md"):
        if any(part.startswith(".") for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            clean_target = target.split("#", 1)[0]
            if clean_target and not (document.parent / clean_target).resolve().exists():
                broken.append(f"{document}: {target}")
    assert broken == []
