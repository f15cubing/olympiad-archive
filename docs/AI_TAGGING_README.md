# AI Tagging System Documentation

## Overview

The AI Tagging system automatically classifies math olympiad problems using Google's Gemini 2.0 Flash API. It analyzes problem statements and solutions to generate structured metadata including field, difficulty, techniques, and topics.

## Features

✅ **Automated Classification** - Analyzes problems and solutions with AI
✅ **Confidence Scoring** - Includes confidence assessment (1-10) for each classification
✅ **Rate Limiting** - Respects API rate limits (1,500 req/day free tier)
✅ **Error Handling** - Robust retry logic and error recovery
✅ **Database Integration** - Stores metadata as JSON for flexibility
✅ **Validation** - Pydantic schema validation for all AI outputs
✅ **Batch Processing** - Efficient batch tagging with configurable batch sizes
✅ **Progress Tracking** - Real-time statistics and progress monitoring

## Architecture

### Modules

```
backend/ai_tagging/
├── __init__.py           # Package exports
├── config.py             # Configuration and constants
├── schemas.py            # Pydantic validation models
├── gemini_client.py      # Gemini API wrapper
├── rate_limiter.py       # Rate limiter (token bucket)
├── db_integration.py     # Database operations
└── tagging_service.py    # Main tagging orchestrator
```

### Data Flow

```
Problem Database
    ↓
Get Untagged Problems (db_integration.py)
    ↓
Build Prompt (gemini_client.py)
    ↓
Call Gemini API (gemini_client.py)
    ↓
Parse & Validate Response (schemas.py)
    ↓
Save Metadata to DB (db_integration.py)
    ↓
Create/Link Tags (db_integration.py)
    ↓
Updated Problem Database
```

## Setup

### 1. Get Gemini API Key

```bash
# Visit: https://aistudio.google.com
# Click "Get API key" → Create new API key in Google AI Studio
# Copy the key and set it as environment variable
```

### 2. Configure Environment

Install `python-dotenv` if you haven't yet:

```bash
pip install python-dotenv
```

The system prefers the newer `google-genai` package for Gemini calls, but if
it isn't installed the code will automatically fall back to the deprecated
`google-generativeai` library. You can continue using either while upgrading.

Create or update `.env` file in the project root:

```bash
# .env
GEMINI_API_KEY=your_api_key_here
```

The Gemini client automatically calls `load_dotenv()` on import, so variables in
`.env` become available at runtime.

Or set as a system environment variable:

```bash
# Linux/Mac
export GEMINI_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"
```
### 3. Verify Setup

```bash
# Test API connection
cd backend
python -c "
from ai_tagging.gemini_client import GeminiClient
client = GeminiClient()
print('✓ Gemini API configured successfully')
"
```

## Usage

### Option 1: Command Line

Tag all untagged problems:
```bash
python tag_problems.py
```

Tag specific problems:
```bash
python tag_problems.py --ids 1 5 12 99
```

Custom batch size:
```bash
python tag_problems.py --batch-size 5
```

Debug mode:
```bash
python tag_problems.py --debug
```

Full help:
```bash
python tag_problems.py --help
```

### Option 2: Python API

```python
import asyncio
from backend.database import AsyncSessionLocal
from backend.ai_tagging import AITaggerService

async def tag_problems():
    async with AsyncSessionLocal() as session:
        service = AITaggerService()

        # Tag all untagged problems
        result = await service.tag_all_untagged(session)

        # Or tag specific problems
        result = await service.tag_batch(session, problem_ids=[1, 2, 3])

        print(f"Success: {result.successful}/{result.total_processed}")
        return result

# Run
result = asyncio.run(tag_problems())
```

### Option 3: FastAPI Endpoint

Add to `backend/routers/tagging.py` (create this file):

```python
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.database import get_db
from backend.ai_tagging import AITaggerService

router = APIRouter(prefix="/api/tags", tags=["tagging"])

@router.post("/tag-all")
async def tag_all(session: AsyncSession = Depends(get_db)):
    """Tag all untagged problems."""
    service = AITaggerService()
    result = await service.tag_all_untagged(session)
    return result

@router.post("/tag-problems")
async def tag_specific(
    problem_ids: list[int] = Query(...),
    session: AsyncSession = Depends(get_db)
):
    """Tag specific problems by IDs."""
    service = AITaggerService()
    result = await service.tag_batch(session, problem_ids=problem_ids)
    return result

@router.get("/statistics")
async def get_stats(session: AsyncSession = Depends(get_db)):
    """Get tagging progress statistics."""
    from backend.ai_tagging.db_integration import get_tagging_statistics
    stats = await get_tagging_statistics(session)
    return stats
```

Then add to `backend/main.py`:

```python
from backend.routers import tagging
app.include_router(tagging.router)
```

## Configuration

Edit `backend/ai_tagging/config.py` to customize:

```python
# API settings
GEMINI_MODEL = "gemini-2.0-flash"  # Model to use
REQUESTS_PER_MINUTE = 25           # Rate limit

# Tag taxonomy
FIELDS = ["Algebra", "Geometry", "Number Theory", "Combinatorics"]
COMMON_TECHNIQUES = [
    "induction",
    "contradiction",
    "pigeonhole",
    "modular arithmetic",
    # ... more
]

# Batch settings
BATCH_SIZE = 10  # Problems per batch

# System prompt
SYSTEM_PROMPT = "..."  # Customize classification instructions
```

## Output Format

### Metadata Structure

Each tagged problem stores JSON metadata:

```json
{
  "analysis": "This problem uses induction to prove a statement about integers.",
  "field": "Number Theory",
  "difficulty": 7,
  "techniques": ["induction", "modular arithmetic"],
  "topics": ["divisibility", "mathematical induction", "inequalities"],
  "confidence_score": 8
}
```

### Auto-Generated Tags

The system automatically creates tags:
- **Field**: `Algebra`, `Geometry`, `Number Theory`, `Combinatorics`
- **Techniques**: `technique: induction`, `technique: pigeonhole`, etc.
- **Topics**: Problem-specific keywords like `cyclic quadrilaterals`, `functional equations`

## API Limits & Costs

### Free Tier (Google AI Studio)
- **Rate**: 1,500 requests per day
- **Throughput**: 1M tokens per minute
- **Cost**: FREE
- **Latency**: ~5-10s per request

### Batch Performance
- 10 problems = ~1 minute
- 1,500 problems = ~2.5 hours
- Full database (assuming 10k problems) = ~16-17 hours

### Cost Estimation
Token estimates per problem:
- Average problem: 200-300 tokens (prompt + response)
- 10 problems: ~2.5k tokens
- Cost per problem: ~$0.0001-0.0003

## Error Handling

### Automatic Retries

The system automatically retries on:
- Rate limit errors (429)
- Server errors (5xx)
- Network timeouts

Retry strategy:
- Up to 3 attempts
- Exponential backoff: 2s → 4s → 8s → 10s max

### Manual Error Recovery

If the script fails partway through:

1. Check the logs for error messages
2. The `tagged_at` column indicates which problems were successfully tagged
3. Re-run the script - it skips already-tagged problems
4. For specific problems: `python tag_problems.py --ids <problem_id>`

## Monitoring & Debugging

### Check Progress

```python
from backend.database import AsyncSessionLocal
from backend.ai_tagging.db_integration import get_tagging_statistics

async def check_progress():
    async with AsyncSessionLocal() as session:
        stats = await get_tagging_statistics(session)
        print(f"Tagged: {stats['tagged_problems']}/{stats['total_problems']}")
        print(f"Progress: {stats['tagging_progress']:.1f}%")
```

### View Recent Tags

```sql
-- SQLite/PostgreSQL
SELECT id, ai_metadata, difficulty, tagged_at
FROM problems
WHERE ai_metadata IS NOT NULL
ORDER BY tagged_at DESC
LIMIT 10;
```

### Debug Specific Problem

```python
async def debug_problem(problem_id: int):
    async with AsyncSessionLocal() as session:
        from backend.ai_tagging.db_integration import get_problem_data
        from backend.ai_tagging import GeminiClient

        data = await get_problem_data(session, problem_id)
        client = GeminiClient()
        result = await client.tag_problem(
            **data
        )

        print(f"Success: {result.success}")
        print(f"Error: {result.error}")
        print(f"AI Metadata: {result.ai_metadata}")
```

## Future Enhancements

- [ ] **Chain-of-Thought (CoT)** - Request reasoning before classification
- [ ] **Few-Shot Learning** - Include examples in the prompt
- [ ] **Self-Assessment** - Have AI critique its own tags
- [ ] **Confidence-Based Filtering** - Auto-flag low-confidence tags for review
- [ ] **Batch Retries** - Resume from specific failed items
- [ ] **Cost Tracking** - Detailed token and cost analytics
- [ ] **Prompt Versioning** - Track which prompt version tagged each problem
- [ ] **A/B Testing** - Compare different prompts on sample set

## Troubleshooting

### Issue: "GEMINI_API_KEY not provided or set in environment"

**Solution**:
1. Get key from https://aistudio.google.com
2. Set environment variable:
   ```bash
   export GEMINI_API_KEY=your_key_here
   # or create .env file with: GEMINI_API_KEY=your_key_here
   ```

### Issue: Rate limit errors after 1,500+ requests

**Solution**:
1. Wait 24 hours (daily limit resets)
2. Or upgrade to paid API plan
3. Reduce REQUESTS_PER_MINUTE in config.py

### Issue: Invalid JSON in response

**Solution**:
1. Check problem statement for unusual formatting
2. Try with --debug flag to see full response
3. Report issue if problem statement is malformed

### Issue: Database locked error

**Solution**:
1. Check if another script is running
2. Close any open database connections
3. Try again in a few seconds

## Support

For issues or questions:
1. Check logs with `--debug` flag
2. Review error messages in results summary
3. Check database schema: `PRAGMA table_info(problems);` (SQLite)

## References

- [Google AI Studio](https://aistudio.google.com)
- [Gemini API Docs](https://ai.google.dev/docs)
- [Free Tier Limits](https://ai.google.dev/pricing#api-pricing)
