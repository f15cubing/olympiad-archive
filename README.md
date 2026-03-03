# Olympiad Archive

A comprehensive digital archive for mathematics olympiad problems with solutions, providing an organized and searchable platform for accessing competition problems from around the world.

## Project Overview

**Olympiad Archive** is a full-stack web application designed to collect, organize, and make accessible a vast repository of mathematics olympiad problems and their solutions. The platform enables students, teachers, and researchers to browse competitions, view problems with solutions, and explore problems by difficulty and topic.

## Key Features

- **Competition Browser**: Browse olympiad competitions organized by country and year
- **Problem Catalog**: Access thousands of olympiad problems with LaTeX-formatted statements
- **Solution Database**: View multiple solutions for each problem
- **Tagging System**: Organize problems by topic/technique (algebra, geometry, combinatorics, etc.)
- **Difficulty Ratings**: Filter problems by difficulty levels (1-10 scale)
- **Math Rendering**: Full KaTeX support for beautiful mathematical notation display

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLAlchemy ORM with async support
- **API**: RESTful API with CORS enabled
- **Testing**: pytest with async support

### Frontend
- **Framework**: React 18 with Vite
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **Math Rendering**: KaTeX + react-katex
- **Testing**: Vitest + React Testing Library
- **HTTP Client**: Axios

## Project Structure

```
olympiad-archive/
├── backend/               # Python FastAPI backend
│   ├── main.py           # Application entry point
│   ├── models.py         # SQLAlchemy ORM models
│   ├── database.py       # Database configuration
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── routers/          # API endpoint handlers
│   ├── tests/            # Test suite
│   └── requirements.txt  # Python dependencies
│
└── frontend/             # React + Vite frontend
    ├── src/
    │   ├── components/   # React components
    │   ├── App.jsx       # Main application component
    │   └── index.css     # Global styles
    ├── package.json      # npm dependencies
    └── vite.config.js    # Vite configuration
```

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Development

### Running Tests

**Backend**:
```bash
cd backend
pytest
```

**Frontend**:
```bash
cd frontend
npm test
```

### Linting

**Backend**:
```bash
# Using your preferred Python linter (e.g., pylint, flake8)
```

**Frontend**:
```bash
cd frontend
npm run lint
```

## Database Models

### Core Entities

- **Competition**: Math olympiad competitions (IMO, AMC, etc.)
- **Problem**: Individual competition problems with LaTeX statements
- **Solution**: Multiple solution approaches per problem
- **Tag**: Topic/technique categorization system

See [backend/README.md](backend/README.md) for detailed model information.

## Contributing

Guidelines for contributing to the Olympiad Archive project:

1. Follow the existing code structure and naming conventions
2. Write tests for new features
3. Keep documentation updated
4. Ensure CORS and API compatibility

## License

[Add your license information here]

## Contact

[Add contact/maintainer information here]

---

For detailed documentation on specific components, see:
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
