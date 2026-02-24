from typing import Iterable, List

import numpy as np
from openai import AsyncOpenAI

from ..utils.config import load_config


class OpenAIEmbedder:
    def __init__(self) -> None:
        config = load_config()
        self.client = AsyncOpenAI(api_key=config.openai.api_key)
        self.model = config.openai.embedding_model

    async def embed_texts(self, texts: Iterable[str]) -> np.ndarray:
        items = list(texts)
        if not items:
            return np.zeros((0, 0), dtype="float32")
        response = await self.client.embeddings.create(model=self.model, input=items)
        vectors = [np.array(e.embedding, dtype="float32") for e in response.data]
        return np.vstack(vectors)

