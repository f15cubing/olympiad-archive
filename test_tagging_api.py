#!/usr/bin/env python3
"""Quick test script for the AI tagging API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000/api"

print("=" * 60)
print("Testing AI Tagging API Implementation")
print("=" * 60)

# Test 1: Get problems
print("\n[1] Fetching problems...")
try:
    resp = requests.get(f"{BASE_URL}/problems")
    problems = resp.json()
    print(f"✓ Found {len(problems)} problems")

    if problems:
        first_problem = problems[0]
        problem_id = first_problem["id"]
        print(f"  First problem ID: {problem_id}")
        print(f"  Has ai_metadata: {first_problem.get('ai_metadata') is not None}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Test 2: Test the single tagging endpoint
print("\n[2] Testing single tagging endpoint...")
try:
    resp = requests.post(f"{BASE_URL}/tagging/{problem_id}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✓ Endpoint accessible")
        print(f"  Response keys: {list(result.keys())}")
        print(f"  Successful: {result.get('successful')} / {result.get('total_processed')}")
    else:
        print(f"✗ Status {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Verify ProblemResponse includes ai_metadata
print("\n[3] Checking if ProblemResponse schema includes ai_metadata...")
try:
    resp = requests.get(f"{BASE_URL}/problems/{problem_id}")
    if resp.status_code == 200:
        problem = resp.json()
        has_ai_metadata_field = "ai_metadata" in problem
        print(f"✓ Problem fetched")
        print(f"  Has ai_metadata field: {has_ai_metadata_field}")
        if has_ai_metadata_field and problem["ai_metadata"]:
            print(f"  AI Metadata: {problem['ai_metadata']}")
    else:
        print(f"✗ Status {resp.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Test batch endpoint
print("\n[4] Testing batch tagging endpoint...")
try:
    resp = requests.post(
        f"{BASE_URL}/tagging/batch",
        json={"problem_ids": [problem_id]}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"✓ Batch endpoint accessible")
        print(f"  Successful: {result.get('successful')} / {result.get('total_processed')}")
    else:
        print(f"✗ Status {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Testing Complete!")
print("=" * 60)
