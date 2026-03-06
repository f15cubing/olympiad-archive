#!/usr/bin/env python3
"""Simple test of the tagging endpoint."""

import requests

# Fetch a problem
resp = requests.get('http://localhost:8000/problems')
problems = resp.json()
if not problems:
    print("No problems found")
    exit(1)

problem_id = problems[0]['id']
print(f"Testing with problem ID: {problem_id}")

# Test tagging endpoint
print("Calling POST /tagging/{problem_id}...")
try:
    resp = requests.post(f'http://localhost:8000/tagging/{problem_id}', timeout=60)
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(f"Result: {result}")

    # Verify response contains expected fields
    expected_fields = ['total_processed', 'successful', 'failed', 'results']
    missing = [f for f in expected_fields if f not in result]
    if missing:
        print(f"WARNING: Missing fields: {missing}")
    else:
        print("✓ All expected fields present")

except Exception as e:
    print(f"Error: {e}")
    exit(1)

# Fetch updated problem to see if ai_metadata is populated
print("\nFetching updated problem...")
resp = requests.get(f'http://localhost:8000/problems/{problem_id}')
problem = resp.json()
print(f"Problem has ai_metadata: {problem.get('ai_metadata') is not None}")
if problem.get('ai_metadata'):
    print(f"AI Metadata: {problem['ai_metadata']}")
