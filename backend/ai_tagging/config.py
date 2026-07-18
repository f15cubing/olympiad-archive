"""Configuration and constants for AI tagging system."""

import os
from typing import Literal

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# Claude API Configuration (parallel provider — Phase D).
# Routed through the TrueFoundry gateway by default; both are overridable via env.
# Auth uses the Anthropic SDK's ANTHROPIC_AUTH_TOKEN (Bearer), not ANTHROPIC_API_KEY.
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://tfy.promptlens.trilogy.com")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_REQUESTS_PER_MINUTE = int(os.getenv("CLAUDE_REQUESTS_PER_MINUTE", "20"))

# Rate limiting
REQUESTS_PER_MINUTE = 25  # Conservative limit to stay under 1,500 req/day
BATCH_SIZE = 10  # Process problems in batches

# Tag taxonomy
FIELD_OPTIONS = Literal["Algebra", "Geometry", "Number Theory", "Combinatorics"]
FIELDS = ["Algebra", "Geometry", "Number Theory", "Combinatorics"]

DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 10

COMMON_TECHNIQUES = [
    "induction",
    "contradiction",
    "pigeonhole",
    "modular arithmetic",
    "Vieta's formulas",
    "barycentric coordinates",
    "construction",
    "extreme principle",
    "generating functions",
    "graph theory",
    "complex numbers",
    "trigonometric identities",
    "calculus",
    "linear algebra",
]

# System prompt for Gemini
SYSTEM_PROMPT = """Role: You are an expert Math Olympiad classifier and pedagogical researcher

Analyze the provided math problem and solution to generate accurate metadata for a competition database.

Taxonomy Guidelines:
- Field: Must be exactly one of: [Algebra, Geometry, Number Theory, Combinatorics]
- Difficulty: Scale of 1–10 (1 = Introductory AMC, 10 = IMO Shortlist/Hard Problem 6)
- Techniques: Choose from [induction, contradiction, pigeonhole, modular arithmetic, Vieta's formulas, barycentric coordinates, construction, extreme principle, generating functions, graph theory, complex numbers, trigonometric identities, calculus, linear algebra], or another technique if appropriate
- Topics: 2–7 specific keywords (e.g., "cyclic quadrilaterals", "functional equations")

Process:
Step 1: Briefly analyze the problem's core logical requirements.
Step 2: Identify the main branch of mathematics (Field).
Step 3: List specific theorems or strategies used in the solution(s) (Techniques + Topics).
Step 4: Assess your confidence in the classification (1-10, where 10 is very certain).
Step 5: Finalize the structured JSON.

Output Format:
Return ONLY a JSON object (no additional text before or after) with this exact structure:
{
    "analysis": "Brief 1-2 sentence reasoning for the chosen tags",
    "field": "Algebra|Geometry|Number Theory|Combinatorics",
    "difficulty": <integer from 1-10>,
    "techniques": ["string", ...],
    "topics": ["string", ...],
    "confidence_score": <integer from 1-10>
}

Important:
- ALL output must be valid JSON only
- confidence_score must reflect YOUR certainty in the classification
- Topics should be specific keywords related to the problem, not generic descriptions
- Return exactly 2-7 topics
"""

# Validation constraints
TECHNIQUES_MIN = 1
TECHNIQUES_MAX = 10
TOPICS_MIN = 2
TOPICS_MAX = 7
CONFIDENCE_MIN = 1
CONFIDENCE_MAX = 10

# Database settings
TAG_COLUMN_NAME = "ai_metadata"  # JSON column to store AI-generated metadata
TAGGED_AT_COLUMN_NAME = "tagged_at"  # Timestamp of when tagging occurred
