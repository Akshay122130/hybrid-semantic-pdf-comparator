"""Core data models for the Hybrid Semantic PDF Comparison Engine."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class ChunkType(str, Enum):
    """Type of extracted document content chunk."""
    TEXT = "text"
    TABLE_CELL = "table_cell"
    LIST_ITEM = "list_item"
    HEADING = "heading"


class MatchStatus(str, Enum):
    """Comparison status for a chunk or pair of chunks."""
    UNCHANGED = "unchanged"
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class SeverityLevel(str, Enum):
    """Severity rating of detected modifications."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Chunk:
    """Atomic content chunk extracted from a document (typically a sentence or table cell).
    
    Preserves hierarchical, spatial, and semantic context.
    """
    id: str
    paragraph_id: str
    original_text: str
    normalized_text: str
    page_num: int
    section: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    type: ChunkType = ChunkType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk instance to a dictionary representation."""
        data = asdict(self)
        data["type"] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Reconstruct a Chunk instance from a dictionary."""
        data_copy = dict(data)
        if "type" in data_copy and isinstance(data_copy["type"], str):
            data_copy["type"] = ChunkType(data_copy["type"])
        if "bbox" in data_copy and data_copy["bbox"] is not None:
            data_copy["bbox"] = tuple(data_copy["bbox"])
        return cls(**data_copy)


@dataclass
class MatchResult:
    """Represents the alignment and comparison outcome between source and target chunks."""
    status: MatchStatus
    source_chunk: Optional[Chunk] = None
    target_chunk: Optional[Chunk] = None
    similarity_score: float = 0.0
    structural_changes: Dict[str, Any] = field(default_factory=dict)
    severity: SeverityLevel = SeverityLevel.NONE
    confidence: float = 1.0
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert match result to a dictionary representation."""
        return {
            "status": self.status.value,
            "source_chunk": self.source_chunk.to_dict() if self.source_chunk else None,
            "target_chunk": self.target_chunk.to_dict() if self.target_chunk else None,
            "similarity_score": self.similarity_score,
            "structural_changes": self.structural_changes,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchResult":
        """Reconstruct a MatchResult instance from a dictionary."""
        data_copy = dict(data)
        data_copy["status"] = MatchStatus(data_copy["status"])
        data_copy["severity"] = SeverityLevel(data_copy["severity"])
        if data_copy.get("source_chunk"):
            data_copy["source_chunk"] = Chunk.from_dict(data_copy["source_chunk"])
        if data_copy.get("target_chunk"):
            data_copy["target_chunk"] = Chunk.from_dict(data_copy["target_chunk"])
        return cls(**data_copy)


@dataclass
class ProcessingStats:
    """Execution metrics and processing statistics for a comparison run."""
    pages_processed: int = 0
    chunks_extracted: int = 0
    exact_matches: int = 0
    semantic_matches: int = 0
    added: int = 0
    removed: int = 0
    ocr_pages: int = 0
    tables_detected: int = 0
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert processing stats to a dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingStats":
        """Reconstruct a ProcessingStats instance from a dictionary."""
        return cls(**data)
