import os
import re
from typing import Any, Dict, Iterable, List

class ResourceSearchTool:
    """Local retrieval tool over uploaded/session resources.

    This is intentionally deterministic: agents do not read files directly.
    The backend extracts relevant snippets and passes them to the planning engine.
    """

    def __init__(self, max_chars_per_resource: int = 60000, chunk_size: int = 900):
        self.max_chars_per_resource = max_chars_per_resource
        self.chunk_size = chunk_size

    def search(self, resources: Iterable[Dict[str, Any]], query: str, limit: int = 6) -> List[Dict[str, Any]]:
        terms = self._terms(query)
        if not terms:
            return []

        hits: List[Dict[str, Any]] = []
        for resource in resources:
            if not isinstance(resource, dict) or self._is_syllabus(resource):
                continue

            text = self._load_text(resource)
            if not text:
                score = self._score(" ".join([str(resource.get("name", "")), str(resource.get("type", ""))]), terms)
                if score:
                    hits.append(self._hit(resource, "", score))
                continue

            for chunk in self._chunks(text):
                score = self._score(f"{resource.get('name', '')}\n{chunk}", terms)
                if score:
                    hits.append(self._hit(resource, chunk, score))

        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:limit]

    def _load_text(self, resource: Dict[str, Any]) -> str:
        content = resource.get("content")
        if isinstance(content, str) and content.strip():
            return content[: self.max_chars_per_resource]

        path = resource.get("path")
        if not path or not isinstance(path, str) or not os.path.exists(path):
            return ""

        lower_path = path.lower()
        try:
            if lower_path.endswith(".pdf"):
                from .pdf import extract_pdf_content

                return extract_pdf_content(path)[: self.max_chars_per_resource]
            if lower_path.endswith((".txt", ".md", ".csv", ".json")):
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    return file.read(self.max_chars_per_resource)
        except Exception:
            return ""
        return ""

    def _chunks(self, text: str) -> Iterable[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        chunks = []
        for start in range(0, len(cleaned), self.chunk_size):
            chunk = cleaned[start : start + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks

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
        score = 0
        for term in terms:
            score += lowered.count(term)
        return score

    def _is_syllabus(self, resource: Dict[str, Any]) -> bool:
        name = str(resource.get("name") or "").lower()
        metadata = resource.get("metadata") or resource.get("resource_metadata") or {}
        metadata_says_syllabus = isinstance(metadata, dict) and metadata.get("is_syllabus") is True
        return metadata_says_syllabus or "syllabus" in name

    def _hit(self, resource: Dict[str, Any], snippet: str, score: int) -> Dict[str, Any]:
        return {
            "id": resource.get("id"),
            "name": str(resource.get("name") or "Resource"),
            "type": str(resource.get("type") or "resource"),
            "path": resource.get("path"),
            "score": score,
            "snippet": snippet[:1200],
        }
