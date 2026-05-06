"""
search.py — Semantic search using Chroma vector store + BGE-m3 embeddings.

Replaces the previous NLTK keyword extraction + SQLite FTS5 approach.
The query is embedded with BGE-m3 (runs locally, no API key needed)
and compared against stored chunk vectors using cosine similarity.
"""

import os
from dotenv import load_dotenv

load_dotenv()

VECTORSTORE_DIR = "./vectorstore"
COLLECTION_NAME = "knowledge_base"
DEFAULT_K       = 5   # number of chunks to retrieve

# Module-level singletons — loaded once when the server starts
_embeddings  = None
_vectorstore = None


def _load_vectorstore():
    """Load Chroma and the BGE-m3 embedding model (once per process)."""
    global _embeddings, _vectorstore

    if _vectorstore is not None:
        return _vectorstore

    if not os.path.exists(VECTORSTORE_DIR):
        raise FileNotFoundError(
            f"Vector store not found at {VECTORSTORE_DIR}. "
            "Run ingest.py first to build it."
        )

    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    _embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    _vectorstore = Chroma(
        persist_directory=VECTORSTORE_DIR,
        embedding_function=_embeddings,
        collection_name=COLLECTION_NAME,
    )

    print("Vector store loaded.")
    return _vectorstore


def search(query: str, k: int = DEFAULT_K) -> list[dict]:
    """
    Perform semantic similarity search against the Chroma vector store.

    The query is embedded with BGE-m3 and compared against all stored chunk
    vectors using cosine similarity. Returns the k most relevant chunks.

    Returns list of:
        {
            source:        filename the chunk came from,
            content:       the chunk text,
            score:         cosine similarity score (higher = more relevant),
            chunk_index:   position of the chunk in the original document,
        }
    """
    vs = _load_vectorstore()

    # similarity_search_with_relevance_scores returns (Document, score) tuples
    results_with_scores = vs.similarity_search_with_relevance_scores(query, k=k)

    results = []
    for doc, score in results_with_scores:
        source = os.path.basename(doc.metadata.get("source", "unknown"))
        results.append({
            "source":      source,
            "content":     doc.page_content,
            "score":       round(score, 4),
            "chunk_index": doc.metadata.get("page", 0),
        })

    # Sort by score descending (most relevant first)
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def format_context(results: list[dict]) -> str:
    """
    Format retrieved chunks into a context string for the LLM prompt.
    Each chunk is wrapped in XML-style tags with its source filename,
    following the structure recommended in the RC architecture document.
    """
    if not results:
        return ""

    parts = [
        f'<document id="{i}" source="{r["source"]}" score="{r["score"]}">\n{r["content"]}\n</document>'
        for i, r in enumerate(results, 1)
    ]
    return "\n\n".join(parts)