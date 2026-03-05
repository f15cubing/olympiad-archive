"""Pydantic schemas for AI tagging validation."""

from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class AITagMetadata(BaseModel):
    """Schema for AI-generated tag metadata from Gemini."""
    
    analysis: str = Field(..., min_length=10, max_length=500)
    field: Literal["Algebra", "Geometry", "Number Theory", "Combinatorics"]
    difficulty: int = Field(..., ge=1, le=10)
    techniques: list[str] = Field(..., min_items=1, max_items=10)
    topics: list[str] = Field(..., min_items=2, max_items=7)
    confidence_score: int = Field(..., ge=1, le=10)
    
    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        """Ensure field is one of the allowed values."""
        allowed = {"Algebra", "Geometry", "Number Theory", "Combinatorics"}
        if v not in allowed:
            raise ValueError(f"field must be one of {allowed}, got {v}")
        return v
    
    @field_validator("techniques")
    @classmethod
    def validate_techniques(cls, v: list[str]) -> list[str]:
        """Ensure techniques are non-empty strings."""
        if not v:
            raise ValueError("techniques list cannot be empty")
        # Clean and validate each technique
        cleaned = [t.strip().lower() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("techniques list contains only empty strings")
        if len(cleaned) > 10:
            raise ValueError("techniques list cannot exceed 10 items")
        return cleaned
    
    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        """Ensure topics are within size bounds."""
        if not 2 <= len(v) <= 7:
            raise ValueError(f"topics must have 2-7 items, got {len(v)}")
        # Clean and validate each topic
        cleaned = [t.strip() for t in v if t.strip()]
        if len(cleaned) != len(v):
            raise ValueError("topics list contains empty strings")
        return cleaned


class ProblemWithSolution(BaseModel):
    """Schema for a problem and its solution for AI processing."""
    
    problem_id: int
    problem_statement: str
    solution_content: str | None = None
    year: int | None = None
    problem_number: int | None = None
    
    @field_validator("problem_statement", "solution_content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        """Ensure content is not empty if provided."""
        if v and not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class TaggingResult(BaseModel):
    """Result of tagging a single problem."""
    
    problem_id: int
    success: bool
    metadata: AITagMetadata | None = None
    error: str | None = None
    tokens_used: int | None = None
    tagged_at: datetime = Field(default_factory=datetime.utcnow)


class TaggingBatchResult(BaseModel):
    """Result of tagging a batch of problems."""
    
    total_processed: int
    successful: int
    failed: int
    results: list[TaggingResult]
    total_tokens: int
    total_cost_estimate: float  # Rough estimate based on tokens
