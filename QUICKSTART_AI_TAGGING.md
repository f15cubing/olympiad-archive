# AI Connection Implementation - Quick Start Guide

## What Was Built

A complete AI-powered automated tagging system for olympiad problems using Google's Gemini 2.0 Flash API.

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **gemini_client.py** | Handles all Gemini API calls with retry logic | `backend/ai_tagging/` |
| **tagging_service.py** | Orchestrates the tagging workflow | `backend/ai_tagging/` |
| **rate_limiter.py** | Manages API rate limits (1,500 req/day) | `backend/ai_tagging/` |
| **db_integration.py** | Database read/write operations | `backend/ai_tagging/` |
| **schemas.py** | Pydantic validation for AI responses | `backend/ai_tagging/` |
| **tag_problems.py** | CLI entry point to run tagging | `root/` |

## 🚀 Quick Start (5 Minutes)

### Step 1: Get Gemini API Key

```bash
# 1. Go to: https://aistudio.google.com
# 2. Click "Get API key" → "Create new API key"
# 3. Copy the key
```

### Step 2: Set Environment Variable

**Option A: Create .env file**
```bash
# Create file: .env (in project root)
GEMINI_API_KEY=your_api_key_here
```

**Option B: Set system variable**
```powershell
# Windows PowerShell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your_api_key_here", "User")
# Then restart terminal

# Or temporarily:
$env:GEMINI_API_KEY="your_api_key_here"
```

### Step 3: Create Database Columns

The system needs two new columns in the `problems` table. Run this:

```bash
# SQLite migration
sqlite3 olympiad.db "
ALTER TABLE problems ADD COLUMN metadata JSON;
ALTER TABLE problems ADD COLUMN tagged_at TIMESTAMP;
"
```

**Or with Python:**
```python
import asyncio
from backend.database import engine
from backend.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())
```

### Step 4: Run AI Tagging

```bash
# Option 1: Tag all untagged problems
python tag_problems.py

# Option 2: Tag specific problems
python tag_problems.py --ids 1 5 12

# Option 3: Custom batch size
python tag_problems.py --batch-size 5

# Option 4: Debug mode
python tag_problems.py --debug
```

**Expected Output:**
```
INFO:__main__:Starting batch tagging for 10 problems
INFO:root:Tagging problem 1...
INFO:root:Successfully tagged problem 1 with confidence 8
...
============================================================
BATCH RESULTS SUMMARY
============================================================
Total Processed: 10
Successfully Tagged: 10
Failed: 0
Total Tokens Used: 2,234
Estimated Cost: $0.0003
============================================================
```

## 📊 What Gets Stored

Each problem gets AI-generated metadata:

```json
{
  "analysis": "Uses induction to prove divisibility property.",
  "field": "Number Theory",
  "difficulty": 7,
  "techniques": ["induction", "modular arithmetic"],
  "topics": ["divisibility", "mathematical induction"],
  "confidence_score": 8
}
```

Plus automatic tag creation:
- Field tags: `Number Theory`, `Algebra`, etc.
- Technique tags: `technique: induction`, `technique: modular arithmetic`
- Topic tags: `divisibility`, `mathematical induction`, etc.

## 🔍 Monitor Progress

```bash
# Check tagging statistics
python -c "
import asyncio
from backend.database import AsyncSessionLocal
from backend.ai_tagging.db_integration import get_tagging_statistics

async def stats():
    async with AsyncSessionLocal() as session:
        s = await get_tagging_statistics(session)
        print(f\"Tagged: {s['tagged_problems']}/{s['total_problems']}\")
        print(f\"Progress: {s['tagging_progress']:.1f}%\")

asyncio.run(stats())
"
```

## 📋 API Limits Reference

| Metric | Value |
|--------|-------|
| Requests/Day | 1,500 |
| Tokens/Minute | 1M |
| Cost | FREE |
| Avg per problem | 2-3 minutes, ~$0.0001-0.0003 |
| Full DB (10k problems) | ~16-17 hours total |

## 🛠️ Use Cases

### Use Case 1: Tag Everything
```bash
python tag_problems.py
```
Best for: Initial setup, batch processing entire DB

### Use Case 2: Tag New Problems
```python
# Add to your problem creation endpoint
from backend.ai_tagging import AITaggerService

async def create_problem(session, problem_data):
    # ... create problem ...
    
    # Auto-tag the new problem
    service = AITaggerService()
    result = await service.tag_batch(session, problem_ids=[problem.id])
```

### Use Case 3: Selective Retag
```bash
# Re-tag specific problems if you improve the prompt
python tag_problems.py --ids 1 2 3 4 5
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "GEMINI_API_KEY not provided" | Set `GEMINI_API_KEY` env var (see Step 2) |
| Rate limit after 1,500 requests | Wait 24 hours (daily limit resets) |
| "Invalid JSON response" | Problem has unusual formatting - check logs |
| Database locked | Close other DB connections |
| Partial completion | Re-run; it skips already-tagged problems |

## 📚 Full Documentation

See **AI_TAGGING_README.md** for:
- Advanced configuration
- Python API usage
- FastAPI endpoint examples
- Error handling details
- Future enhancements
- Complete troubleshooting guide

## ✅ Next Steps

1. **Get API Key** - https://aistudio.google.com
2. **Set GEMINI_API_KEY** - Create .env file or set env var
3. **Update Database** - Run ALTER TABLE commands
4. **Run Tagging** - `python tag_problems.py`
5. **Monitor Progress** - Use statistics commands
6. **(Optional) Add Endpoints** - See API docs in README

## 🎯 Architecture (High Level)

```
tag_problems.py (CLI)
    ↓
AITaggerService (orchestration)
    ├→ Get untagged problems (database)
    ├→ For each problem:
    │   ├→ GeminiClient (API call)
    │   ├→ Validate response (Pydantic)
    │   └→ Save to database
    └→ Print results
```

## 💡 Pro Tips

1. **Start small** - Tag 5-10 problems first to verify setup
2. **Monitor tokens** - First run shows estimated cost
3. **Batch size** - Smaller batches (5-10) for better error recovery
4. **Debugging** - Use `--debug` flag to see full API responses
5. **Resume** - If interrupted, just re-run; skips already-tagged

---

**Questions?** Check AI_TAGGING_README.md for detailed documentation.
