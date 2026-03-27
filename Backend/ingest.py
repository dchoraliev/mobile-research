"""
ingest.py — Run once to populate the SQLite FTS5 knowledge base.

Usage:
    python ingest.py --source ./docs

Supported file types: .txt, .pdf
Each file is split into overlapping chunks stored in the knowledge_base table.
Re-running is safe — existing chunks for a file are replaced.
"""

import argparse
import os
import re
import sqlite3

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("PyMuPDF not installed — PDF support disabled. Run: pip install pymupdf")

DB_PATH = "knowledge.db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_base
        USING fts5(source, chunk_index, content)
    """)
    conn.commit()


def chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def extract_txt(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_pdf(path: str) -> str:
    if not PDF_SUPPORT:
        print(f"  Skipping {path} — PyMuPDF not installed")
        return ""
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def ingest_file(conn: sqlite3.Connection, filepath: str) -> None:
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    print(f"  Ingesting: {filename}")

    if ext == ".txt":
        text = extract_txt(filepath)
    elif ext == ".pdf":
        text = extract_pdf(filepath)
    else:
        print(f"  Skipping unsupported type: {ext}")
        return

    if not text.strip():
        print(f"  No text found in {filename}")
        return

    chunks = chunk_text(text)
    conn.execute("DELETE FROM knowledge_base WHERE source = ?", (filename,))
    conn.executemany(
        "INSERT INTO knowledge_base (source, chunk_index, content) VALUES (?, ?, ?)",
        [(filename, i, chunk) for i, chunk in enumerate(chunks)],
    )
    conn.commit()
    print(f"  → {len(chunks)} chunks stored")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest docs into SQLite FTS5")
    parser.add_argument("--source", default="./docs", help="Folder with .txt/.pdf files")
    parser.add_argument("--db", default=DB_PATH, help="SQLite DB path")
    args = parser.parse_args()

    if not os.path.isdir(args.source):
        print(f"Directory not found: {args.source}")
        return

    conn = sqlite3.connect(args.db)
    init_db(conn)

    files = [
        os.path.join(args.source, f)
        for f in os.listdir(args.source)
        if f.lower().endswith((".txt", ".pdf"))
    ]

    if not files:
        print(f"No .txt or .pdf files found in {args.source}")
        return

    print(f"Found {len(files)} file(s) in {args.source}")
    for f in files:
        ingest_file(conn, f)

    conn.close()
    print(f"\nDone. Knowledge base: {args.db}")


if __name__ == "__main__":
    main()