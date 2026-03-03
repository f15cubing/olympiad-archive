# Olympiad Archive Frontend

A modern React application for browsing and exploring mathematics olympiad problems and solutions.

## Overview

The frontend provides an intuitive interface for discovering olympiad problems from competitions around the world. Users can browse competitions, filter by years, view detailed problem statements with LaTeX rendering, and access multiple solutions for each problem.

## Tech Stack

- **Framework**: React 18.3.1
- **Build Tool**: Vite 5.1.4
- **Routing**: React Router DOM 6.22.0
- **Styling**: Tailwind CSS 4.2.1
- **Math Rendering**: KaTeX 0.16.9 + react-katex 3.0.2
- **HTTP Client**: Axios 1.6.0
- **Testing**: Vitest 1.3.1 + React Testing Library 14.2.1
- **Linting**: ESLint 8.56.0

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── CompetitionList.jsx  # List of competitions
│   │   ├── YearList.jsx         # Years for a competition
│   │   ├── ProblemList.jsx      # Problems for a year
│   │   └── ProblemDetail.jsx    # Detailed problem view with solutions
│   ├── __tests__/           # Component tests
│   │   ├── CompetitionList.test.jsx
│   │   ├── ProblemList.test.jsx
│   │   └── YearList.test.jsx
│   ├── assets/              # Images, fonts, static assets
│   ├── App.jsx              # Main app wrapper with routing
│   ├── App.css              # App-level styles
│   ├── index.css            # Global styles
│   ├── main.jsx             # Application entry point
│   └── setupTests.js        # Test configuration
├── public/                  # Static public assets
├── package.json             # Dependencies and scripts
├── vite.config.js          # Vite configuration
├── vitest.config.js        # Vitest testing configuration
├── eslint.config.js        # ESLint configuration
└── index.html              # HTML template
```

## Components

### CompetitionList
Displays all available olympiad competitions.

**Features:**
- List of all competitions
- Filter by country/name
- Links to year selection for each competition

**Usage:**
```jsx
<CompetitionList />
```

### YearList
Shows all years available for a selected competition.

**Props:**
- `compId`: Competition ID (from URL params)

**Features:**
- Years sorted chronologically
- Problem count per year
- Navigation to problem list

### ProblemList
Displays problems for a selected competition and year.

**Props:**
- `compId`: Competition ID
- `year`: Problem year

**Features:**
- Problem list with difficulty ratings
- Filter by difficulty or tags
- Quick access to problem details
- Sorting options

### ProblemDetail
Detailed view of a single problem with solutions.

**Props:**
- `id`: Problem ID (from URL params)

**Features:**
- Full problem statement with LaTeX rendering
- Problem metadata (author, difficulty, tags)
- Multiple solutions with KaTeX rendering
- Solution source/author information

## Routing

The application uses React Router v6 with the following routes:

```
/ → CompetitionList
/competition/:compId → YearList
/competition/:compId/:year → ProblemList
/problem/:id → ProblemDetail
```

## Getting Started

### Prerequisites
- Node.js 16+ or npm 8+

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Ensure the backend API is running on `http://localhost:8000`

### Development

Start the development server with hot reload:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build

Create an optimized production build:
```bash
npm run build
```

Output will be in the `dist/` directory.

### Preview

Preview the production build locally:
```bash
npm run preview
```

## Testing

### Run Tests
```bash
npm test
```

### Watch Mode
```bash
npm test -- --watch
```

### Coverage
```bash
npm test -- --coverage
```

### Test Files

Tests are located in `src/__tests__/` with the naming convention `*.test.jsx`:

- **CompetitionList.test.jsx**: Tests for competition listing
- **YearList.test.jsx**: Tests for year selection
- **ProblemList.test.jsx**: Tests for problem browsing

Example test structure:
```javascript
import { render, screen } from '@testing-library/react';
import CompetitionList from '../CompetitionList';

describe('CompetitionList', () => {
  it('should render a list of competitions', () => {
    render(<CompetitionList />);
    expect(screen.getByText(/competitions/i)).toBeInTheDocument();
  });
});
```

## Linting

Run ESLint to check code quality:
```bash
npm run lint
```

Fix linting issues automatically:
```bash
npm run lint -- --fix
```

### Configured Rules
- React best practices (react plugin)
- React Hooks compliance (react-hooks plugin)
- React Refresh compatibility (react-refresh plugin)

## API Integration

### Axios Configuration

The frontend communicates with the backend API at `http://localhost:8000`.

Example API calls:

```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

// Fetch competitions
axios.get(`${API_BASE}/competitions`)

// Fetch problems for a competition/year
axios.get(`${API_BASE}/competitions/${compId}/${year}`)

// Fetch problem details
axios.get(`${API_BASE}/problems/${problemId}`)

// Fetch solutions
axios.get(`${API_BASE}/problems/${problemId}/solutions`)
```

### Error Handling

Implement error handling for API calls:
```javascript
try {
  const response = await axios.get(url);
  // Handle success
} catch (error) {
  if (error.response?.status === 404) {
    // Handle not found
  } else {
    // Handle other errors
  }
}
```

## Styling

### Tailwind CSS

The project uses Tailwind CSS for utility-first styling.

Key classes used:
- Layout: `min-h-screen`, `bg-slate-50`, `flex`, `grid`
- Typography: `text-lg`, `font-bold`, `text-slate-700`
- Spacing: `p-4`, `m-2`, `gap-4`
- Interactive: `hover:`, `focus:`, `active:`

Example component styling:
```jsx
<div className="min-h-screen bg-slate-50 p-8">
  <h1 className="text-3xl font-bold text-slate-900">Problems</h1>
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {/* Content */}
  </div>
</div>
```

### KaTeX Rendering

Mathematical expressions are rendered using KaTeX through the `react-katex` package.

```javascript
import { InlineMath, BlockMath } from 'react-katex';

// Inline math
<InlineMath math="x^2 + y^2 = z^2" />

// Display math
<BlockMath math="\int_0^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}" />
```

Problem statements and solutions contain LaTeX, which is automatically rendered with proper formatting.

## Environment Variables

Create a `.env` file in the frontend directory (if needed):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Olympiad Archive
```

Access in code:
```javascript
const apiBase = import.meta.env.VITE_API_BASE_URL;
```

## Performance Optimization

### Code Splitting
React Router automatically code-splits at route boundaries with Vite.

### Image Optimization
Place optimized images in `src/assets/` for automatic processing.

### Lazy Loading
```javascript
import { lazy, Suspense } from 'react';

const ProblemDetail = lazy(() => import('./components/ProblemDetail'));

// In component
<Suspense fallback={<Loading />}>
  <ProblemDetail />
</Suspense>
```

## Common Issues

### API Connection Errors
1. Verify backend is running on `http://localhost:8000`
2. Check CORS settings in backend `main.py`
3. Ensure frontend URL is in backend's `allow_origins`

### KaTeX Rendering Issues
1. Check problem statement LaTeX syntax
2. Ensure `react-katex` is properly imported
3. Verify KaTeX CSS is loaded

### Build Errors
1. Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
2. Clear Vite cache: `rm -rf .vite`
3. Check Node.js version: `node --version`

## Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Hosting

#### Vercel
```bash
npm install -g vercel
vercel
```

#### Netlify
```bash
npm run build
# Deploy the dist/ folder
```

#### Docker
```dockerfile
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:18
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
CMD ["serve", "-s", "dist", "-l", "5173"]
```

Build and run:
```bash
docker build -t olympiad-frontend .
docker run -p 5173:5173 olympiad-frontend
```

## Future Enhancements

- [ ] Search functionality for problems
- [ ] Advanced filtering (by difficulty, tags, author)
- [ ] Problem bookmarking/favorites
- [ ] User authentication
- [ ] Dark mode support
- [ ] Mobile app version
- [ ] Problem recommendation engine
- [ ] Export to PDF

## Contributing

1. Follow Code of Conduct
2. Use ESLint for code quality
3. Write tests for new features
4. Ensure all tests pass
5. Update documentation

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

[Add your license information here]

---

For backend documentation, see [../backend/README.md](../backend/README.md)
