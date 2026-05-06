"""
ingest.py — Run once to build the Chroma vector store from docs/.

Usage:
    python ingest.py --source ./docs

Supported file types: .txt, .pdf
Each file is split into overlapping chunks, embedded with BGE-m3 (local,
no API key needed), and stored in the Chroma vector database at ./vectorstore/.

Re-running is safe — the collection is deleted and rebuilt from scratch.
"""

import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ── Config ───────────────────────────────────────────────────────────────────
VECTORSTORE_DIR = "./vectorstore"
COLLECTION_NAME = "knowledge_base"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 100


def load_documents(source_dir: str) -> list:
    """Load all .txt and .pdf files from the source directory."""
    documents = []

    # Load .txt files
    txt_loader = DirectoryLoader(
        source_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
        show_progress=True,
    )
    txt_docs = txt_loader.load()
    print(f"  Loaded {len(txt_docs)} .txt file(s)")
    documents.extend(txt_docs)

    # Load .pdf files
    pdf_loader = DirectoryLoader(
        source_dir,
        glob="**/*.pdf",
        loader_cls=PyMuPDFLoader,
        show_progress=True,
    )
    pdf_docs = pdf_loader.load()
    print(f"  Loaded {len(pdf_docs)} .pdf file(s)")
    documents.extend(pdf_docs)

    return documents


def split_documents(documents: list) -> list:
    """Split documents into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # Try to split on paragraphs, then sentences, then words
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    return chunks


def build_vectorstore(chunks: list) -> Chroma:
    """Embed all chunks locally with BGE-m3 and store them in Chroma."""
    # BGE-m3 runs entirely on your machine — no API key, no rate limits.
    # First run downloads the model (~570MB). Subsequent runs use the cache.
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    # Delete existing collection so re-running is always clean
    if os.path.exists(VECTORSTORE_DIR):
        import shutil
        shutil.rmtree(VECTORSTORE_DIR)
        print(f"  Removed existing vectorstore at {VECTORSTORE_DIR}")

    print(f"  Embedding {len(chunks)} chunks with BGE-m3 — this may take a moment...")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTORSTORE_DIR,
        collection_name=COLLECTION_NAME,
    )

    return vectorstore


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest docs into Chroma vector store")
    parser.add_argument("--source", default="./docs", help="Folder with .txt/.pdf files")
    args = parser.parse_args()

    if not os.path.isdir(args.source):
        print(f"Directory not found: {args.source}")
        return

    print(f"\n── Step 1: Loading documents from {args.source}")
    documents = load_documents(args.source)

    if not documents:
        print("No .txt or .pdf files found — nothing to ingest.")
        return

    print(f"  Total documents loaded: {len(documents)}")

    print(f"\n── Step 2: Splitting into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    chunks = split_documents(documents)
    print(f"  Total chunks created: {len(chunks)}")

    # Show a summary of chunks per source file
    from collections import Counter
    sources = Counter(
        os.path.basename(c.metadata.get("source", "unknown")) for c in chunks
    )
    for source, count in sorted(sources.items()):
        print(f"    {source}: {count} chunks")

    print(f"\n── Step 3: Building Chroma vector store at {VECTORSTORE_DIR}")
    vectorstore = build_vectorstore(chunks)

    print(f"\nDone. Vector store saved to {VECTORSTORE_DIR}/")
    print(f"Total chunks embedded: {len(chunks)}")


if __name__ == "__main__":
    main()