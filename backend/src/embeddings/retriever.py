from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

from ..rules.chunker import RuleChunk
from ..utils.config import load_config
from .embedder import OpenAIEmbedder
from .vector_store import FaissVectorStore


@dataclass
class RetrievedRule:
    text: str
    metadata: dict
    score: float


class RuleRetriever:
    def __init__(self) -> None:
        config = load_config()
        self.embedder = OpenAIEmbedder()
        self.store = FaissVectorStore(
            dim=0,
            index_path=Path(config.rules.faiss_index_path),
            meta_path=Path(config.rules.faiss_meta_path),
        )
        self.store.load_if_exists()

    async def build_index_if_needed(self, chunks: List[RuleChunk]) -> None:
        if not self.store.is_empty():
            return
        texts = [c.text for c in chunks]
        vectors = await self.embedder.embed_texts(texts)
        metadatas = [c.metadata for c in chunks]
        self.store.add(vectors, metadatas)
        self.store.save()

    async def retrieve(self, query: str, top_k: int) -> List[RetrievedRule]:
        vectors = await self.embedder.embed_texts([query])
        results = self.store.search(vectors, top_k=top_k)[0]
        retrieved: List[RetrievedRule] = []
        for meta, dist in results:
            rule_text = meta.get("text", "")
            retrieved.append(RetrievedRule(text=rule_text, metadata=meta, score=dist))
        return retrieved


def prepare_chunks_for_store(chunks: List[RuleChunk]) -> List[RuleChunk]:
    prepared: List[RuleChunk] = []
    for chunk in chunks:
        meta = dict(chunk.metadata)
        meta["text"] = chunk.text
        prepared.append(RuleChunk(id=chunk.id, text=chunk.text, metadata=meta))
    return prepared

