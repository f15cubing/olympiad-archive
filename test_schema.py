#!/usr/bin/env python3
"""Test schema serialization with mock AI metadata."""

import sys
sys.path.insert(0, '.')

from backend.schemas import ProblemResponse, AIMetadataResponse
from datetime import datetime

# Test AIMetadataResponse directly
print("Testing AIMetadataResponse schema...")
ai_meta_data = {
    "field": "Algebra",
    "techniques": ["induction", "factorization"],
    "topics": ["polynomials", "sequences"],
    "tagged_at": datetime.now()
}

try:
    ai_response = AIMetadataResponse(**ai_meta_data)
    print(f"✓ AIMetadataResponse created: {ai_response}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Test ProblemResponse with ai_metadata
print("\nTesting ProblemResponse with ai_metadata...")
problem_data = {
    "id": 1,
    "year": 2023,
    "problem_number": 1,
    "statement": "Solve for x: $x^2 = 4$",
    "competition_id": 1,
    "ai_metadata": ai_meta_data
}

try:
    problem_response = ProblemResponse(**problem_data)
    print(f"✓ ProblemResponse created with ai_metadata")
    print(f"  Field: {problem_response.ai_metadata.field}")
    print(f"  Techniques: {problem_response.ai_metadata.techniques}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Test dict-to-model conversion (like from database)
print("\nTesting dict-to-model conversion (database scenario)...")
problem_with_dict_meta = {
    "id": 2,
    "year": 2023,
    "problem_number": 2,
    "statement": "Prove that...",
    "competition_id": 1,
    "ai_metadata": {
        "field": "Geometry",
        "techniques": ["coordinate geometry"],
        "topics": ["triangles", "circles"],
        "tagged_at": datetime.now().isoformat()
    }
}

try:
    problem_response2 = ProblemResponse(**problem_with_dict_meta)
    print(f"✓ ProblemResponse created from dict ai_metadata")
    print(f"  Field: {problem_response2.ai_metadata.field if problem_response2.ai_metadata else 'None'}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

print("\n" + "="*50)
print("All schema tests passed!")
print("="*50)
