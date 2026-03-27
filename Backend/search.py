"""
search.py — Keyword extraction (NLTK) + SQLite FTS5 search.
"""

import re
import sqlite3

DB_PATH = "knowledge.db"
MAX_RESULTS = 5

# NLTK stopwords — loaded lazily
_STOPWORDS: set[str] | None = None


def _stopwords() -> set[str]:
    global _STOPWORDS
    if _STOPWORDS is None:
        try:
            from nltk.corpus import stopwords
            import nltk
            try:
                _STOPWORDS = set(stopwords.words("english"))
            except LookupError:
                nltk.download("stopwords", quiet=True)
                _STOPWORDS = set(stopwords.words("english"))
        except ImportError:
            # NLTK not installed — fall back to a small built-in set
            _STOPWORDS = {
                "a", "an", "the", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "shall", "can",
                "to", "of", "in", "for", "on", "with", "at", "by", "from",
                "as", "into", "through", "about", "this", "that", "these",
                "those", "i", "you", "he", "she", "it", "we", "they",
                "what", "which", "who", "how", "when", "where", "why",
                "and", "or", "but", "not", "if", "so",
            }
    return _STOPWORDS


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords using NLTK stopwords."""
    words = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
    stop = _stopwords()
    return [w for w in words if w not in stop]


def build_fts_query(keywords: list[str]) -> str:
    """Build an FTS5 OR query from keywords."""
    if not keywords:
        return ""
    # Use OR so partial matches still return results
    return " OR ".join(keywords[:20])  # cap to avoid overly long queries


def search(
    query: str,
    db_path: str = DB_PATH,
    max_results: int = MAX_RESULTS,
) -> list[dict]:
    """
    Search the knowledge base for chunks matching the query.
    Returns list of { source, chunk_index, content, score }.
    """
    keywords = extract_keywords(query)
    fts_query = build_fts_query(keywords)

    if not fts_query:
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT source, chunk_index, content, rank AS score
            FROM knowledge_base
            WHERE knowledge_base MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, max_results),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        print(f"Search error: {e}")
        return []


def format_context(results: list[dict]) -> str:
    """Format search results into a context string for the prompt."""
    if not results:
        return ""
    parts = [
        f"[{i}] (from {r['source']}):\n{r['content']}"
        for i, r in enumerate(results, 1)
    ]
    return "\n\n".join(parts)