import os
import re
from typing import Dict, Iterable, List


class MethodologySearchTool:
    """Small local RAG helper over repo-versioned study methodology notes."""

    def __init__(self, base_dir: str | None = None, chunk_size: int = 900):
        self.base_dir = base_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge", "methodology")
        self.chunk_size = chunk_size

    def search(self, query: str, limit: int = 5) -> List[Dict[str, str | int]]:
        terms = self._terms(query)
        if not terms:
            return []

        hits = []
        for doc in self._documents():
            for chunk in self._chunks(doc["content"]):
                score = self._score(f"{doc['title']} {chunk}", terms)
                if score:
                    hits.append({
                        "title": doc["title"],
                        "source": doc["source"],
                        "score": score,
                        "snippet": chunk[:1200],
                    })
        hits.sort(key=lambda item: int(item["score"]), reverse=True)
        return hits[:limit]

    def _documents(self) -> Iterable[Dict[str, str]]:
        if not os.path.isdir(self.base_dir):
            return []
        docs = []
        for filename in sorted(os.listdir(self.base_dir)):
            if not filename.endswith((".md", ".txt")):
                continue
            path = os.path.join(self.base_dir, filename)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
            except OSError:
                continue
            docs.append({
                "title": os.path.splitext(filename)[0].replace("_", " ").title(),
                "source": filename,
                "content": content,
            })
        return docs

    def _chunks(self, text: str) -> List[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        return [cleaned[start:start + self.chunk_size].strip() for start in range(0, len(cleaned), self.chunk_size)]

    def _terms(self, query: str) -> List[str]:
        stop_words = {
            "about", "after", "again", "also", "and", "are", "because", "but", "can",
            "create", "day", "days", "for", "from", "has", "have", "how", "into",
            "make", "need", "plan", "study", "that", "the", "this", "to", "use",
            "with", "your",
        }
        return [
            term
            for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", query.lower())
            if term not in stop_words
        ]

    def _score(self, text: str, terms: List[str]) -> int:
        lowered = text.lower()
        return sum(lowered.count(term) for term in terms)
