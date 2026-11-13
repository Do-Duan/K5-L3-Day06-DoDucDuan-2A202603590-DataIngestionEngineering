"""Ingest the DOCX with real OpenRouter embeddings into pgvector."""
import os
from pathlib import Path
from dotenv import load_dotenv
from .ingestion import load_docx
from .chunking import by_paragraph
from .embeddings import MyEmbedder
from .store import PgVectorStore


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    root = Path(__file__).resolve().parents[2]
    doc_path = Path(os.getenv("DOCX_PATH", str(root / "starter" / "data" / "Capstone Project Document.docx")))
    model = os.getenv("EMBEDDING_MODEL")
    db_url = os.getenv("DATABASE_URL")
    if not model or not db_url:
        raise RuntimeError("Set EMBEDDING_MODEL and DATABASE_URL in starter/.env")
    source = str(doc_path.resolve().relative_to(root.resolve()))
    units = load_docx(doc_path, "capstone-project-document", source)
    chunks = [chunk for unit in units for chunk in by_paragraph(unit, 900)]
    embedder = MyEmbedder(model)
    vectors = embedder.embed_documents([c.text for c in chunks])
    store = PgVectorStore(db_url, embedder.dimensions)
    store.create_schema()
    store.upsert("paragraph-v1", chunks, vectors)
    print(f"Ingested {len(units)} source units into {len(chunks)} chunks")
    print(f"Embedding model: {model}; dimensions: {embedder.dimensions}")
    print("Example query: python -m src.run --query \"What does the project investigate?\"")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query")
    parser.add_argument("--filter", action="append", default=[], help="metadata key=value")
    args = parser.parse_args()
    if args.query:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        model, db_url = os.getenv("EMBEDDING_MODEL"), os.getenv("DATABASE_URL")
        if not model or not db_url:
            raise RuntimeError("Set EMBEDDING_MODEL and DATABASE_URL in starter/.env")
        embedder = MyEmbedder(model)
        vector = embedder.embed_query(args.query)
        filters = dict(item.split("=", 1) for item in args.filter)
        hits = PgVectorStore(db_url, embedder.dimensions).search("paragraph-v1", vector, 3, filters)
        for hit in hits:
            print(hit)
    else:
        main()
