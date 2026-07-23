"""
search.py — Semantic search using Chroma vector store + BGE-m3 embeddings.

The query is embedded with BGE-m3 (runs locally, no API key needed)
and compared against stored chunk vectors using cosine similarity.
Embedding and retrieval are timed separately for measurement purposes.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

VECTORSTORE_DIR = "./vectorstore"
COLLECTION_NAME = "knowledge_base"
DEFAULT_K       = 10

_embeddings  = None
_vectorstore = None


def _load_vectorstore():
    """Load Chroma and BGE-m3 once per process."""
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


def search(query: str, k: int = DEFAULT_K) -> tuple[list[dict], dict]:
    """
    Semantic similarity search against the Chroma vector store.

    Returns:
        results: list of {source, content, score, chunk_index}
        timings: {embedding_ms, retrieval_ms}
    """
    vs = _load_vectorstore()

    # Time embedding separately
    t0 = time.time()
    _embeddings.embed_query(query)
    embedding_ms = (time.time() - t0) * 1000

    # Time retrieval separately
    t1 = time.time()
    results_with_scores = vs.similarity_search_with_relevance_scores(query, k=k)
    retrieval_ms = (time.time() - t1) * 1000

    results = []
    for doc, score in results_with_scores:
        source = os.path.basename(doc.metadata.get("source", "unknown"))
        results.append({
            "source":      source,
            "content":     doc.page_content,
            "score":       round(score, 4),
            "chunk_index": doc.metadata.get("page", 0),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    timings = {
        "embedding_ms": round(embedding_ms, 2),
        "retrieval_ms": round(retrieval_ms, 2),
    }
    return results, timings


def format_context(results: list[dict]) -> str:
    """Format retrieved chunks as XML-tagged context for the LLM prompt."""
    if not results:
        return ""
    parts = [
        f'<document id="{i}" source="{r["source"]}" score="{r["score"]}">\n{r["content"]}\n</document>'
        for i, r in enumerate(results, 1)
    ]
    return "\n\n".join(parts)