# Olympiad Archive - Codebase Summary

## Project Overview

**Olympiad Archive** is a full-stack web application designed to catalog, organize, and provide access to mathematics olympiad problems from competitions worldwide. The platform allows users to browse competitions, view problems with complete solutions, and explore problems by difficulty and topic areas.

**Status**: Active Development
**Architecture**: Full-Stack (FastAPI Backend + React Frontend)
**Database**: SQLAlchemy ORM (supports SQLite, PostgreSQL)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser / Client                         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────────┐
│          Frontend (React + Vite)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Routes:                                              │  │
│  │ • / → CompetitionList                               │  │
│  │ • /competition/:compId → YearList                   │  │
│  │ • /competition/:compId/:year → ProblemList          │  │
│  │ • /problem/:id → ProblemDetail                      │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                                                  │
│           ├─ Components: CompetitionList, YearList,         │
│           │              ProblemList, ProblemDetail         │
│           │                                                  │
│           └─ Styling: Tailwind CSS + KaTeX Math Rendering   │
└────────────────────┬────────────────────────────────────────┘
                     │ CORS Request
┌────────────────────▼────────────────────────────────────────┐
│          Backend (FastAPI)                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ API Endpoints:                                       │  │
│  │ • GET/POST /competitions (CRUD)                      │  │
│  │ • GET/POST /problems (CRUD)                          │  │
│  │ • GET/POST /solutions (CRUD)                         │  │
│  │ • GET/POST /tags (CRUD)                              │  │
│  │ • GET /competitions/{id}/years (Custom)              │  │
│  │ • GET /competitions/{id}/{year} (Custom)             │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                                                  │
│           ├─ Routers: competitions, problems, solutions,    │
│           │            tags                                 │
│           │                                                  │
│           └─ Models: SQLAlchemy ORM with async support      │
└────────────────────┬────────────────────────────────────────┘
                     │ SQL Queries
┌────────────────────▼────────────────────────────────────────┐
│          Database (SQLAlchemy)                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Tables:                                              │  │
│  │ • competitions: name, country, url                   │  │
│  │ • problems: statement, year, difficulty, tags       │  │
│  │ • solutions: content, author, problem_id             │  │
│  │ • tags: name (many-to-many with problems)            │  │
│  │ • problem_tags: junction table                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Backend Structure

### Directory Layout
```
backend/
├── main.py              # FastAPI app initialization & routes
├── database.py          # Database connection and config
├── models.py            # SQLAlchemy ORM models (4 entities)
├── schemas.py           # Pydantic request/response schemas
├── seed.py              # Database seeding utility
├── routers/             # Modular API route handlers
│   ├── competitions.py  # Competition CRUD operations
│   ├── problems.py      # Problem CRUD + custom queries
│   ├── solutions.py     # Solution CRUD operations
│   └── tags.py          # Tag CRUD + filtering
├── tests/               # Test suite
│   ├── conftest.py      # pytest fixtures (async DB setup)
│   ├── test_api.py      # Endpoint integration tests
│   └── __pycache__/
├── requirements.txt     # Python dependencies
└── pytest.ini          # pytest configuration
```

### Key Components

#### Core Models (models.py)
1. **Competition**: Olympiad competitions (IMO, AMC, etc.)
   - Fields: id, name, country, url
   - Relations: One → Many Problems

2. **Problem**: Individual competition problems
   - Fields: id, competition_id, year, problem_number, statement (LaTeX), author, difficulty (1-10), source_url, created_at
   - Relations: Many → One Competition, Many → Many Tags, One → Many Solutions
   - Lazy loading: `selectin` for performance

3. **Solution**: Problem solutions with explanations
   - Fields: id, problem_id, content (LaTeX), author, created_at
   - Relations: Many → One Problem
   - Supports multiple solutions per problem

4. **Tag**: Topic categorization (algebra, geometry, etc.)
   - Fields: id, name (unique)
   - Relations: Many → Many Problems via `problem_tags` junction table

#### Database Architecture
- **ORM**: SQLAlchemy 2.0 with async/await support
- **Drivers**:
  - SQLite (aiosqlite) - Development
  - PostgreSQL (asyncpg) - Production-ready
- **Auto-initialization**: Tables created on app startup via lifespan context manager

#### API Routers

**routers/competitions.py**
- `GET /competitions` - List all with optional filtering
- `GET /competitions/{id}` - Fetch single with relationships
- `POST /competitions` - Create new
- `PUT /competitions/{id}` - Update
- `DELETE /competitions/{id}` - Delete
- `GET /competitions/{id}/years` - Custom: Get available years

**routers/problems.py**
- `GET /problems` - Paginated list with filters
- `GET /problems/{id}` - Detail view with solutions and tags
- `POST /problems` - Create with associations
- `PUT /problems/{id}` - Update
- `DELETE /problems/{id}` - Delete
- `GET /competitions/{comp_id}/{year}` - Custom: Problems by competition and year

**routers/solutions.py**
- `GET /problems/{id}/solutions` - List solutions for problem
- `POST /problems/{id}/solutions` - Add solution
- `DELETE /solutions/{id}` - Remove solution

**routers/tags.py**
- `GET /tags` - List all tags with problem counts
- `POST /tags` - Create new tag
- `GET /tags/{id}` - Get tag with associated problems
- `GET /problems/tag/{tag_name}` - Filter problems by tag

#### Dependencies
- **fastapi**: Web framework
- **sqlalchemy**: ORM
- **aiosqlite/asyncpg**: Async DB drivers
- **pydantic**: Data validation
- **python-dotenv**: Environment configuration
- **google-genai**: AI integration (optional, replaces deprecated google-generativeai; dotenv support added)
- **pytest**: Testing framework

### Testing
- Location: `tests/` directory
- Framework: pytest with async support
- Structure: Fixtures in conftest.py, tests in test_api.py
- Database: In-memory SQLite for test isolation

---

## Frontend Structure

### Directory Layout
```
frontend/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── CompetitionList.jsx   # Browse all competitions
│   │   ├── YearList.jsx          # Select year for competition
│   │   ├── ProblemList.jsx       # Browse problems in year
│   │   └── ProblemDetail.jsx     # View problem + solutions
│   ├── __tests__/           # Component tests
│   │   ├── CompetitionList.test.jsx
│   │   ├── ProblemList.test.jsx
│   │   └── YearList.test.jsx
│   ├── assets/              # Images, fonts, media
│   ├── App.jsx              # Root component with routing
│   ├── App.css              # Global styles
│   ├── index.css            # Reset & base styles
│   ├── main.jsx             # React entry point
│   └── setupTests.js        # Test configuration
├── public/                  # Static assets served directly
├── package.json             # Dependencies & npm scripts
├── vite.config.js          # Build & HMR configuration
├── vitest.config.js        # Testing setup
├── eslint.config.js        # Code quality rules
├── tailwind.config.js       # Tailwind customization
└── index.html              # HTML template
```

### Component Hierarchy & Data Flow

```
App.jsx (Router)
├── /
│   └── CompetitionList
│       ├── Fetch: GET /competitions
│       └── Render: List → onClick → navigate to YearList
│
├── /competition/:compId
│   └── YearList
│       ├── Fetch: GET /competitions/{compId}/years
│       └── Render: Years → onClick → navigate to ProblemList
│
├── /competition/:compId/:year
│   └── ProblemList
│       ├── Fetch: GET /competitions/{compId}/{year}
│       ├── Features: Filter by difficulty/tags, sort
│       └── Render: Problems → onClick → navigate to ProblemDetail
│
└── /problem/:id
    └── ProblemDetail
        ├── Fetch:
        │   ├── GET /problems/{id} (statement, metadata)
        │   └── GET /problems/{id}/solutions (all solutions)
        ├── Render: Statement (LaTeX) + Solutions (LaTeX)
        └── Features: Solution viewer, metadata display
```

### Key Features

**CompetitionList Component**
- Displays all competitions in a card/grid layout
- Each card shows: Competition name, country, number of problems
- Click to navigate to year selection for that competition

**YearList Component**
- Shows available years for selected competition
- Displays year and total problems for each year
- Click to view problems for specific year/competition

**ProblemList Component**
- Paginated/scrollable list of problems
- Each row: Problem number, year, title, difficulty (1-10 stars), tags
- Filtering: By difficulty range, by tag selection
- Sorting: By number, by difficulty, by year
- Click to view full problem details

**ProblemDetail Component**
- Full page problem view
- Sections:
  - Problem statement (LaTeX rendered)
  - Metadata: Competition, year, author, difficulty, tags
  - Solutions tab: Multiple solutions with authors
- Features: Copy to clipboard, full-screen math view

### Styling System

**Tailwind CSS**
- Utility-first CSS framework
- Custom config in `tailwind.config.js`
- Used for: Layout, spacing, typography, colors, responsive design

**Color Palette** (Slate theme)
- Primary: `slate-50`, `slate-100`, `slate-700`, `slate-900`
- Interactive: `hover:bg-blue-50`, `focus:ring-blue-500`
- Text: `text-slate-700`, `text-slate-900`

**Responsive Breakpoints**
- Base (mobile): No prefix
- `md:` (768px): Tablet
- `lg:` (1024px): Desktop
- `xl:` (1280px): Large desktop

**KaTeX Math Rendering**
- Package: `react-katex` wrapping KaTeX
- Used for: Problem statements, solutions
- Components: `<InlineMath>` for inline, `<BlockMath>` for display
- LaTeX from backend rendered directly

### API Integration

**Axios Instance**
```javascript
const API_BASE = 'http://localhost:8000'
// Requests go to backend on port 8000
// Frontend runs on port 5173 (Vite default)
```

**Endpoints Used**
- `GET /competitions` → CompetitionList
- `GET /competitions/{compId}/years` → YearList
- `GET /competitions/{compId}/{year}` → ProblemList
- `GET /problems/{id}` → ProblemDetail
- `GET /problems/{id}/solutions` → ProblemDetail

### Testing Framework

**Vitest** (Vite-native testing)
- Configuration: `vitest.config.js`
- Setup: Mock server workers (MSW) for API interception
- Libraries: React Testing Library for component testing

**Test Files**
- `CompetitionList.test.jsx`: Rendering, navigation, data loading
- `YearList.test.jsx`: Year selection, filtering
- `ProblemList.test.jsx`: Problem list, sorting, filtering

### Dependencies
- **react**: UI library
- **react-dom**: React DOM rendering
- **react-router-dom**: Client-side routing
- **axios**: HTTP client
- **katex** + **react-katex**: Math rendering
- **tailwindcss**: Styling framework
- **vite**: Build tool & dev server
- **vitest**: Testing framework
- **eslint**: Code linting

---

## Data Model & Relationships

### Entity Relationship Diagram

```
competitions
│
├─ id (PK)
├─ name
├─ country
├─ url
└─ 1:N → problems

    problems
    │
    ├─ id (PK)
    ├─ competition_id (FK)
    ├─ year
    ├─ problem_number
    ├─ statement (LaTeX)
    ├─ author
    ├─ difficulty (1-10)
    ├─ source_url
    ├─ created_at
    │
    ├─ N:1 ← competition
    ├─ 1:N → solutions
    └─ M:N → tags (via problem_tags junction)
        │
        ├─ 1:N solutions
        │   └─ id (PK)
        │      problem_id (FK)
        │      content (LaTeX)
        │      author
        │      created_at
        │
        └─ N:N tags
            └─ id (PK)
               name (unique)
               M:N → problems
```

### Key Relationships

1. **Competition → Problems** (1:N)
   - One competition has many problems
   - Foreign Key: `problem.competition_id`
   - Delete Cascade: Deleting competition cascades to problems

2. **Problem → Solutions** (1:N)
   - One problem has multiple solutions
   - Foreign Key: `solution.problem_id`
   - Delete Cascade: Deleting problem cascades to solutions
   - Eager Loading: `selectin` for performance

3. **Problem ↔ Tags** (M:N)
   - Many problems can have many tags
   - Junction Table: `problem_tags`
   - No delete cascade: Tags persist when problems deleted
   - Eager Loading: `selectin`

---

## Development Workflow

### Local Development Setup

**Prerequisites**
- Python 3.8+ (backend)
- Node.js 16+ (frontend)
- Git

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload  # Starts on http://localhost:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:5173
```

### Database Initialization
- Tables auto-created on backend startup
- Optional seed data available: `python backend/seed.py`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing
- Backend: `pytest` in backend directory
- Frontend: `npm test` in frontend directory

---

## Key Features Summary

### Implemented
✅ Full CRUD for Competitions, Problems, Solutions, Tags
✅ Multi-year problem browsing per competition
✅ Difficulty ratings and tagging system
✅ LaTeX rendering for problems and solutions
✅ RESTful API with comprehensive documentation
✅ Responsive UI with Tailwind CSS
✅ Component-based React architecture
✅ Async database operations for scalability

### In Development / Planned
- 🔲 User authentication and authorization
- 🔲 Bookmarking/favorites system
- 🔲 Advanced search across all problems
- 🔲 Problem recommendation engine
- 🔲 Solution rating/voting system
- 🔲 Export to PDF functionality
- 🔲 Dark mode UI
- 🔲 Mobile app version

---

## Performance Considerations

### Backend
- **Async Operations**: All DB queries are non-blocking (asyncio)
- **Eager Loading**: Using SQLAlchemy `selectin` to reduce N+1 queries
- **Connection Pooling**: Async connection management
- **CORS**: Configured for specific origin to prevent abuse

### Frontend
- **Code Splitting**: Vite automatically splits at route boundaries
- **Lazy Loading**: React.lazy for ProblemDetail component
- **Caching**: Browser cache for static assets
- **KaTeX**: Math rendering cached after first compilation

---

## Deployment Architecture

### Backend Deployment Options
1. **Docker Containerization**: Dockerfile in backend root
2. **Cloud Platforms**: Compatible with AWS, Azure, GCP
3. **Database**: Switch from SQLite to PostgreSQL for production

### Frontend Deployment
1. **Build**: `npm run build` → `dist/` folder
2. **Platforms**: Vercel, Netlify, AWS S3 + CloudFront
3. **Docker**: Multi-stage build for optimized image

---

## Security Considerations

### Current Implementation
- ✅ CORS enabled for specific origin
- ✅ Input validation via Pydantic
- ⚠️ No authentication (development mode)
- ⚠️ No rate limiting

### Production Recommendations
- Implement JWT authentication
- Add rate limiting (slow down abuse)
- Use HTTPS everywhere
- Implement CORS for production domains
- Add API key management
- Database encryption at rest

---

## File Dependencies & Import Structure

### Backend Dependencies
```
main.py
├── imports: database, models, routers (all 4), fastapi, CORS
├── depends on: All routers and models

models.py
├── imports: sqlalchemy
└── no dependencies on other local modules

database.py
├── imports: sqlalchemy
└── provides: engine, async_session for all routers

routers/*.py
├── import: database, schemas, models
└── depend on: database session, models
```

### Frontend Dependencies
```
main.jsx
└── imports: App, React, ReactDOM

App.jsx
├── imports: Router from React Router
├── imports: All 4 components
└── provides: Route definitions

components/*.jsx
├── import: axios, react hooks, react-router
├── import: react-katex (for Detail component)
└── no inter-component imports (flat structure)
```

---

## File Sizes & Complexity

### Backend
- `models.py`: ~53 lines (4 models, relationships)
- `main.py`: ~35 lines (app setup, middleware)
- `routers/*.py`: ~40-50 lines each (CRUD endpoints × 4)
- Total: ~200-250 lines of application code

### Frontend
- `App.jsx`: ~20 lines (routing setup)
- `components/*.jsx`: ~50-100 lines each (4 components)
- `CSS files`: ~100-200 lines combined
- Total: ~400-500 lines of application code

**Overall**: Relatively lightweight codebase suitable for active development and scaling.

---

## Maintenance Notes

### Common Development Tasks

1. **Add New Tag Type**
   - Add to database via POST /tags
   - Frontend auto-discovers via GET /tags

2. **Add New Problem Field**
   - Add column to `Problem` model
   - Add to `ProblemSchema` (Pydantic)
   - Update routers/problems.py
   - Update frontend components

3. **Add New Endpoint**
   - Create function in appropriate router
   - Add Pydantic schema for validation
   - Update API docs (auto-generated)

4. **Update UI Component**
   - Modify component in `src/components/`
   - Run `npm test` to verify
   - Test with dev server running

---

## Version History

- **v0.1.0**: Initial commit - Basic CRUD operations, React UI, routing structure
- **Current**: Active development phase

---

## Next Steps for Development

1. Implement comprehensive test coverage
2. Add user authentication (JWT)
3. Implement problem search functionality
4. Add filtering UI improvements
5. Setup CI/CD pipeline (GitHub Actions)
6. Database backup/migration tools
7. Admin panel for content management

---

End of Codebase Summary
