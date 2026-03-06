# Olympiad Archive Backend

A FastAPI-based REST API for managing mathematics olympiad problems, solutions, and competitions.

## Overview

The backend provides a robust API for storing and retrieving olympiad problem data, including competitions, problems with LaTeX-formatted statements, solutions, and topic tags. The API supports full CRUD operations and is designed to be scalable and maintainable.

## Tech Stack

- **Framework**: FastAPI 0.133.0
- **ORM**: SQLAlchemy 2.0.47 with async support
- **Database Driver**: aiosqlite (SQLite) / asyncpg (PostgreSQL)
- **Validation**: Pydantic 2.12.5
- **Testing**: pytest
- **Additional**: python-dotenv, google-genai (AI integration; replaces deprecated google-generativeai)

## Project Structure

```
backend/
├── main.py              # FastAPI application setup
├── database.py          # Database connection and configuration
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic schemas for request/response validation
├── seed.py              # Database seeding script
├── routers/             # API route handlers
│   ├── competitions.py  # /competitions endpoints
│   ├── problems.py      # /problems endpoints
│   ├── solutions.py     # /solutions endpoints
│   └── tags.py          # /tags endpoints
├── tests/               # Test suite
│   ├── conftest.py      # pytest fixtures
│   ├── test_api.py      # API endpoint tests
│   └── ...
├── requirements.txt     # Python dependencies
└── pytest.ini          # pytest configuration
```

## Database Models

### Competition
```python
- id (Integer, Primary Key)
- name (Text, Required) - Competition name (e.g., 'IMO', 'AMC')
- country (Text, Optional) - Organization country
- url (Text, Optional) - Official competition website
- problems (Relationship) - Associated problems
```

### Problem
```python
- id (Integer, Primary Key)
- competition_id (Integer, Foreign Key)
- year (Integer, Required)
- problem_number (Integer, Required)
- statement (Text, Required) - LaTeX-formatted problem statement
- author (Text, Optional) - Problem creator
- difficulty (Integer, Optional) - 1-10 scale
- source_url (Text, Optional) - Problem source link
- created_at (Timestamp) - Auto-generated creation timestamp
- tags (Relationship) - Associated topic tags
- solutions (Relationship) - Associated solutions
```

### Solution
```python
- id (Integer, Primary Key)
- problem_id (Integer, Foreign Key)
- content (Text, Required) - LaTeX-formatted solution
- author (Text, Default: 'Official')
- created_at (Timestamp) - Auto-generated creation timestamp
```

### Tag
```python
- id (Integer, Primary Key)
- name (Text, Required, Unique) - Topic name (e.g., 'algebra', 'geometry')
- problems (Relationship) - Associated problems (many-to-many)
```

## API Endpoints

### Competitions
- `GET /competitions` - List all competitions
- `GET /competitions/{id}` - Get competition by ID
- `POST /competitions` - Create new competition
- `PUT /competitions/{id}` - Update competition
- `DELETE /competitions/{id}` - Delete competition

### Problems
- `GET /problems` - List all problems (with filtering)
- `GET /problems/{id}` - Get problem by ID with solutions and tags
- `POST /problems` - Create new problem
- `PUT /problems/{id}` - Update problem
- `DELETE /problems/{id}` - Delete problem
- `GET /competitions/{comp_id}/years` - Get years available for competition
- `GET /competitions/{comp_id}/{year}` - Get problems for competition/year

### Solutions
- `GET /problems/{id}/solutions` - List solutions for a problem
- `POST /problems/{id}/solutions` - Create solution for problem
- `DELETE /solutions/{id}` - Delete solution

### Tags
- `GET /tags` - List all tags
- `POST /tags` - Create new tag
- `GET /tags/{id}` - Get tag by ID with associated problems

## Getting Started

### Prerequisites
- Python 3.8+
- pip or conda

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file (if using environment variables):
   ```
   DATABASE_URL=sqlite+aiosqlite:///olympiad.db
   ```

3. Seed the database (optional):
   ```bash
   python seed.py
   ```

### Running the Server

Development mode with hot reload:
```bash
uvicorn main:app --reload
```

Production mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running:
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

## Testing

Run the test suite:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_api.py
```

Run with coverage:
```bash
pytest --cov=.
```

## Configuration

Key configuration points in `main.py`:

### CORS Settings
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Update `allow_origins` for production deployments.

### Database Initialization
The application automatically creates all tables on startup via the lifespan context manager:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```

## Database

### Supported Databases
- **SQLite**: Default, suitable for development (`aiosqlite`)
- **PostgreSQL**: For production (`asyncpg`)

### Switching Databases
Update `DATABASE_URL` in `database.py`:

SQLite:
```python
DATABASE_URL = "sqlite+aiosqlite:///olympiad.db"
```

PostgreSQL:
```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/olympiad_db"
```

## Deployment

### Docker

Create a `Dockerfile` in the backend directory:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t olympiad-api .
docker run -p 8000:8000 olympiad-api
```

### Environment Variables

Create a `.env` file for sensitive configuration:
```
DATABASE_URL=
ALLOWED_ORIGINS=
```

## Dependencies Management

Key dependencies explained:

- **fastapi**: Modern web framework for building APIs
- **sqlalchemy**: SQL toolkit and ORM
- **aiosqlite/asyncpg**: Async database drivers
- **pydantic**: Data validation using Python type hints
- **python-dotenv**: Environment variable management
- **pytest**: Testing framework
- **google-genai**: (Optional) AI-powered solution generation (preferred)

To update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

## Common Issues

### CORS Errors
If frontend can't communicate with API, check:
1. Frontend URL is in `allow_origins` in `main.py`
2. Backend is running on the expected port
3. API requests include correct base URL

### Database Errors
- Ensure database file/server is accessible
- Check database URL format in `database.py`
- Verify database user permissions (if using PostgreSQL)

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python path includes the backend directory

## Future Enhancements

- [ ] Advanced filtering and search capabilities
- [ ] User authentication and authorization
- [ ] Caching layer (Redis)
- [ ] Full-text search on problem statements
- [ ] Problem recommendation system
- [ ] Export functionality (PDF, etc.)

## Contributing

1. Follow PEP 8 style guidelines
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass before submitting PRs

## License

[Add your license information here]

---

For frontend documentation, see [../frontend/README.md](../frontend/README.md)
