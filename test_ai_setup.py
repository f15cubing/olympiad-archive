#!/usr/bin/env python
"""Test script to verify AI tagging system is properly configured."""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_gemini_api():
    """Test Gemini API connection."""
    print("🧪 Testing Gemini API Connection...")
    try:
        from backend.ai_tagging.gemini_client import GeminiClient
        
        client = GeminiClient()
        print("   ✅ GeminiClient initialized successfully")
        
        # Try a simple test request
        test_problem = "What is 2 + 2?"
        response = await client._call_gemini(test_problem)
        print("   ✅ API response received (simple test)")
        
        return True
    except ValueError as e:
        if "GEMINI_API_KEY" in str(e):
            print("   ❌ GEMINI_API_KEY not set. Please:")
            print("      1. Get key from https://aistudio.google.com")
            print("      2. Create .env file with: GEMINI_API_KEY=your_key_here")
            print("      3. Or set environment variable")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


async def test_database_connection():
    """Test database connection."""
    print("\n🧪 Testing Database Connection...")
    try:
        from backend.database import AsyncSessionLocal
        from backend.models import Problem
        
        async with AsyncSessionLocal() as session:
            # Try a simple query
            from sqlalchemy import select, func
            result = await session.execute(select(func.count(Problem.id)))
            count = result.scalar()
            print(f"   ✅ Database connected. Total problems: {count}")
            return True
    except Exception as e:
        print(f"   ❌ Database error: {str(e)}")
        return False


async def test_schemas():
    """Test Pydantic schemas."""
    print("\n🧪 Testing Pydantic Schemas...")
    try:
        from backend.ai_tagging.schemas import AITagMetadata
        
        # Test valid metadata
        test_data = {
            "analysis": "This is a test problem using induction.",
            "field": "Number Theory",
            "difficulty": 5,
            "techniques": ["induction"],
            "topics": ["divisibility", "induction"],
            "confidence_score": 8
        }
        
        metadata = AITagMetadata(**test_data)
        print("   ✅ Valid metadata passes validation")
        
        # Test invalid difficulty
        try:
            invalid_data = test_data.copy()
            invalid_data["difficulty"] = 15  # Out of range
            AITagMetadata(**invalid_data)
            print("   ❌ Invalid metadata should have failed validation")
            return False
        except ValueError:
            print("   ✅ Invalid metadata correctly rejected")
        
        return True
    except Exception as e:
        print(f"   ❌ Schema error: {str(e)}")
        return False


async def test_rate_limiter():
    """Test rate limiter."""
    print("\n🧪 Testing Rate Limiter...")
    try:
        from backend.ai_tagging.rate_limiter import RateLimiter
        import time
        
        limiter = RateLimiter(requests_per_minute=5)
        
        # Make 3 quick requests
        start = time.time()
        for i in range(3):
            await limiter.check_limit()
        elapsed = time.time() - start
        
        print(f"   ✅ Rate limiter working (3 requests in {elapsed:.2f}s)")
        return True
    except Exception as e:
        print(f"   ❌ Rate limiter error: {str(e)}")
        return False


async def test_cli_script():
    """Test CLI script exists and is executable."""
    print("\n🧪 Testing CLI Script...")
    try:
        cli_path = Path(__file__).parent / "tag_problems.py"
        if cli_path.exists():
            print(f"   ✅ CLI script found at {cli_path}")
            return True
        else:
            print(f"   ❌ CLI script not found at {cli_path}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking CLI: {str(e)}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("AI TAGGING SYSTEM - CONFIGURATION TEST")
    print("=" * 60)
    
    tests = [
        ("Gemini API", test_gemini_api),
        ("Database", test_database_connection),
        ("Schemas", test_schemas),
        ("Rate Limiter", test_rate_limiter),
        ("CLI Script", test_cli_script),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except Exception as e:
            print(f"\n   ❌ Unexpected error in {name}: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
    
    print("=" * 60)
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! You're ready to run:")
        print("   python tag_problems.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
