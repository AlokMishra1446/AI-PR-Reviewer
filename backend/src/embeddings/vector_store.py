import json
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np


class FaissVectorStore:
    def __init__(self, dim: int, index_path: Path, meta_path: Path) -> None:
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.index = faiss.IndexFlatL2(dim)
        self.metadata: List[Dict[str, str]] = []

    def is_empty(self) -> bool:
        return self.index.ntotal == 0

    def add(self, vectors: np.ndarray, metadatas: List[Dict[str, str]]) -> None:
        if vectors.dtype != np.float32:
            vectors = vectors.astype("float32")
        if self.is_empty():
            self.index = faiss.IndexFlatL2(vectors.shape[1])
            self.dim = vectors.shape[1]
        self.index.add(vectors)
        self.metadata.extend(metadatas)

    def save(self) -> None:
        if not self.index_path.parent.exists():
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with self.meta_path.open("w", encoding="utf-8") as f:
            json.dump(self.metadata, f)

    def load_if_exists(self) -> None:
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with self.meta_path.open("r", encoding="utf-8") as f:
                self.metadata = json.load(f)

    def search(self, query_vectors: np.ndarray, top_k: int) -> List[List[Tuple[Dict[str, str], float]]]:
        if self.is_empty():
            return [[] for _ in range(len(query_vectors))]
        if query_vectors.dtype != np.float32:
            query_vectors = query_vectors.astype("float32")
        distances, indices = self.index.search(query_vectors, top_k)
        results: List[List[Tuple[Dict[str, str], float]]] = []
        for i in range(len(query_vectors)):
            row: List[Tuple[Dict[str, str], float]] = []
            for j, idx in enumerate(indices[i]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                row.append((self.metadata[idx], float(distances[i][j])))
            results.append(row)
        return results

