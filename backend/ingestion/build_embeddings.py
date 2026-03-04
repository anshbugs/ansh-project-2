from __future__ import annotations

"""
Phase 2 – Build Embedding Index

CLI usage (from project root):

    python -m backend.ingestion.build_embeddings

This script:
- Reads all text chunks from kb_chunks.
- For any chunk that does NOT yet have an embedding in kb_chunk_embeddings,
  it calls the OpenRouter embeddings endpoint (via backend.openrouter_client)
  to compute an embedding vector.
- Stores embeddings as JSON text in the kb_chunk_embeddings table.
"""

import json
import logging
from typing import List, Tuple

from backend.db import get_connection, init_db
from backend.local_embeddings import embed_texts


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_unembedded_chunks(batch_size: int = 32) -> List[Tuple[str, str]]:
    """
    Return a batch of (chunk_id, content) for chunks that do not yet have embeddings.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.chunk_id, c.content
            FROM kb_chunks c
            LEFT JOIN kb_chunk_embeddings e
              ON c.chunk_id = e.chunk_id
            WHERE e.chunk_id IS NULL
            LIMIT ?;
            """,
            (batch_size,),
        )
        rows = cur.fetchall()
        return [(row[0], row[1]) for row in rows]
    finally:
        conn.close()


def insert_embeddings(rows: List[Tuple[str, List[float]]]) -> None:
    """
    Persist embeddings into kb_chunk_embeddings.
    """
    if not rows:
        return
    conn = get_connection()
    try:
        cur = conn.cursor()
        for chunk_id, embedding in rows:
            embedding_json = json.dumps(embedding)
            cur.execute(
                """
                INSERT INTO kb_chunk_embeddings (chunk_id, embedding_json)
                VALUES (?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    embedding_json=excluded.embedding_json;
                """,
                (chunk_id, embedding_json),
            )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    init_db()
    total_processed = 0
    while True:
        batch = load_unembedded_chunks(batch_size=32)
        if not batch:
            logging.info("No more chunks without embeddings. Processed %d chunks.", total_processed)
            break

        chunk_ids = [cid for cid, _ in batch]
        texts = [content for _, content in batch]
        logging.info("Embedding batch of %d chunks", len(chunk_ids))

        try:
            embeddings = embed_texts(texts)
        except Exception as exc:  # noqa: BLE001
            logging.error("Embedding request failed: %s", exc)
            break

        insert_rows = list(zip(chunk_ids, embeddings))
        insert_embeddings(insert_rows)
        total_processed += len(chunk_ids)

    logging.info("Embedding build complete. Total chunks processed: %d", total_processed)


if __name__ == "__main__":
    main()

