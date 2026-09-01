"""Semantic candidate retrieval using Sentence Transformers and FAISS."""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

# Disable TensorFlow imports in Transformers to avoid Py3.13 TF compatibility issues
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

try:
    import faiss
    from sentence_transformers import SentenceTransformer

except ImportError:  # pragma: no cover
    faiss = None
    SentenceTransformer = None

from pdf_comparator.core.models import Chunk


@dataclass
class CandidateMatch:
    """A single candidate match from Document B for a given Document A chunk.
    
    Contains similarity score and references to source/target Chunk objects.
    """
    source_chunk: Chunk
    target_chunk: Chunk
    source_id: str
    target_id: str
    similarity_score: float


@dataclass
class SemanticRetrievalResult:
    """Output structure containing top-k candidate matches grouped by source chunk ID."""
    candidates_by_source: Dict[str, List[CandidateMatch]] = field(default_factory=dict)

    def get_candidates(self, source_id: str) -> List[CandidateMatch]:
        """Retrieve the ranked candidate list for a given source chunk ID."""
        return self.candidates_by_source.get(source_id, [])


class SemanticRetriever:
    """Retrieves top-k semantically similar candidate chunks using local embeddings and FAISS.
    
    Architectural Purpose:
        CANDIDATE RETRIEVAL ONLY. This component does NOT make final correspondence
        or modification decisions. It filters candidate chunks from Document B for
        each unresolved chunk in Document A based on vector cosine similarity.
        
    Embedding & FAISS Optimization:
        - Uses Sentence Transformers (default: 'all-MiniLM-L6-v2').
        - The model is loaded once and cached across queries.
        - Embeddings are L2-normalized (`normalize_embeddings=True`) so inner product (IP)
          in FAISS is mathematically identical to cosine similarity.
        - Batch encoding is used for all target chunks in one operation.
        - A single FAISS `IndexFlatIP` is built over Document B candidates and reused for
          all Document A candidate queries.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model_instance: Optional[object] = None,
    ):
        """Initialize SemanticRetriever.

        Args:
            model_name: SentenceTransformers model identifier.
            model_instance: Optional pre-loaded model instance (useful for mocking/caching).
        """
        self.model_name = model_name
        self._model = model_instance

    def _get_model(self) -> object:
        """Lazy-load and cache the SentenceTransformer model instance."""
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers package is required for SemanticRetriever. "
                    "Please install sentence-transformers and faiss-cpu."
                )
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def retrieve_candidates(
        self,
        unmatched_a: List[Chunk],
        unmatched_b: List[Chunk],
        top_k: int = 5,
        minimum_similarity: float = -1.0,
    ) -> SemanticRetrievalResult:

        """Retrieve top-k candidate matches from unmatched_b for each chunk in unmatched_a.

        Args:
            unmatched_a: Unresolved chunks from Document A.
            unmatched_b: Unresolved candidate chunks from Document B.
            top_k: Maximum number of candidate matches to retrieve per source chunk.
            minimum_similarity: Minimum cosine similarity score threshold (0.0 to 1.0).

        Returns:
            SemanticRetrievalResult containing candidate matches per source chunk ID.
        """
        if not unmatched_a or not unmatched_b:
            return SemanticRetrievalResult(
                candidates_by_source={c.id: [] for c in unmatched_a}
            )

        if faiss is None:
            raise ImportError(
                "faiss package is required for SemanticRetriever. "
                "Please install faiss-cpu."
            )

        model = self._get_model()

        # Prepare text lists for batch encoding
        texts_b = [c.normalized_text if c.normalized_text else c.original_text for c in unmatched_b]
        texts_a = [c.normalized_text if c.normalized_text else c.original_text for c in unmatched_a]

        # 1. Generate normalized embeddings for Document B (target candidate pool)
        embeddings_b = model.encode(
            texts_b,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        # 2. Build FAISS inner product index for Document B
        dimension = embeddings_b.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings_b)

        # 3. Generate normalized embeddings for Document A (query pool)
        embeddings_a = model.encode(
            texts_a,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        # 4. Search top-k candidates in FAISS
        k = min(top_k, len(unmatched_b))
        scores, indices = index.search(embeddings_a, k)

        candidates_by_source: Dict[str, List[CandidateMatch]] = {}

        for i, source_chunk in enumerate(unmatched_a):
            candidate_list: List[CandidateMatch] = []
            for rank in range(k):
                idx = int(indices[i][rank])
                if idx < 0 or idx >= len(unmatched_b):
                    continue

                raw_score = float(scores[i][rank])
                # Clamp score to [-1.0, 1.0] range
                sim_score = max(-1.0, min(1.0, raw_score))

                if sim_score >= minimum_similarity:
                    target_chunk = unmatched_b[idx]
                    candidate = CandidateMatch(
                        source_chunk=source_chunk,
                        target_chunk=target_chunk,
                        source_id=source_chunk.id,
                        target_id=target_chunk.id,
                        similarity_score=sim_score,
                    )
                    candidate_list.append(candidate)

            candidates_by_source[source_chunk.id] = candidate_list

        return SemanticRetrievalResult(candidates_by_source=candidates_by_source)
