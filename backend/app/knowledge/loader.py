from pathlib import Path

from app.domain.models import Document


def load_documents(documents_dir: Path) -> list[Document]:
    if not documents_dir.exists():
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    documents: list[Document] = []
    for path in sorted(documents_dir.glob("*.md")):
        body = path.read_text(encoding="utf-8").strip()
        title, category, content = _parse_front_matter(body, fallback_title=path.stem)
        documents.append(
            Document(
                doc_id=path.stem,
                title=title,
                category=category,
                content=content,
            )
        )
    return documents


def _parse_front_matter(body: str, fallback_title: str) -> tuple[str, str, str]:
    title = fallback_title.replace("_", " ").title()
    category = "general"
    content = body
    if body.startswith("---"):
        _, meta, content = body.split("---", 2)
        for line in meta.splitlines():
            if line.startswith("title:"):
                title = line.removeprefix("title:").strip()
            elif line.startswith("category:"):
                category = line.removeprefix("category:").strip()
        content = content.strip()
    return title, category, content
