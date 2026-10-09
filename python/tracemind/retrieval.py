
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_DIR = PROJECT_ROOT / "knowledge_base" / "runbooks"


def load_runbooks() -> list[dict]:
    documents = []

    for file_path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")

        # Split each runbook into searchable sections.
        sections = []
        current_heading = "Overview"
        current_lines = []

        for line in content.splitlines():
            if line.startswith("#"):
                if current_lines:
                    sections.append({
                        "heading": current_heading,
                        "text": "\n".join(current_lines).strip(),
                    })

                current_heading = line.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "heading": current_heading,
                "text": "\n".join(current_lines).strip(),
            })

        for section in sections:
            if section["text"]:
                documents.append({
                    "source": file_path.name,
                    "heading": section["heading"],
                    "text": section["text"],
                })

    return documents


def search_runbooks(query: str, top_k: int = 3) -> list[dict]:
    if not query.strip():
        return []

    documents = load_runbooks()

    if not documents:
        return []

    texts = [
        f"{doc['heading']}\n{doc['text']}"
        for doc in documents
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
    )

    try:
        document_vectors = vectorizer.fit_transform(texts)
        query_vector = vectorizer.transform([query])
    except ValueError:
        return []

    scores = cosine_similarity(
        query_vector, document_vectors
    ).flatten()

    ranked_indices = scores.argsort()[::-1]

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        # Ignore sections with no meaningful term overlap.
        if score <= 0:
            continue

        doc = documents[index]

        results.append({
            "source": doc["source"],
            "heading": doc["heading"],
            "text": doc["text"],
            "score": round(score, 4),
        })

        if len(results) >= max(1, top_k):
            break

    return results
