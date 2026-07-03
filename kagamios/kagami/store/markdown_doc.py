import re
from dataclasses import dataclass

import yaml

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
SECTION_OPEN_RE = re.compile(r'<!-- sec:(?P<id>[\w-]+) title="(?P<title>[^"]*)" -->\n')


def _close_marker(section_id: str) -> str:
    return f"<!-- /sec:{section_id} -->"


@dataclass
class Section:
    id: str
    title: str
    body: str


def render_document(frontmatter: dict, sections: list[Section]) -> str:
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    parts = [f"---\n{fm_text}\n---\n"]
    for section in sections:
        parts.append(
            f'<!-- sec:{section.id} title="{section.title}" -->\n'
            f"{section.body}\n"
            f"{_close_marker(section.id)}\n"
        )
    return "\n".join(parts)


def parse_document(text: str) -> tuple[dict, list[Section]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("document is missing frontmatter")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)

    sections: list[Section] = []
    pos = 0
    while True:
        open_match = SECTION_OPEN_RE.search(body, pos)
        if not open_match:
            break
        section_id = open_match.group("id")
        title = open_match.group("title")
        close_marker = _close_marker(section_id)
        close_idx = body.index(close_marker, open_match.end())
        section_body = body[open_match.end() : close_idx].strip("\n")
        sections.append(Section(section_id, title, section_body))
        pos = close_idx + len(close_marker)
    return frontmatter, sections
