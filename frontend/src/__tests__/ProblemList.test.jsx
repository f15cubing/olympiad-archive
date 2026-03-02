import { render, screen, waitFor } from '@testing-library/react'
import ProblemList from '../components/ProblemList'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const problemsData = [
  { id: 1, competition_id: 5, year: 2022, problem_number: 1, statement: 'Test $x^2$' },
  { id: 2, competition_id: 5, year: 2022, problem_number: 2, statement: 'Another' },
]

const server = setupServer(
  rest.get('http://localhost:8000/problems/', (req, res, ctx) => {
    return res(ctx.json(problemsData))
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders list of problems for given competition and year', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/year/2022']}>
      <Routes>
        <Route path="/competition/:compId/year/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  expect(screen.getByText(/Loading problems/i)).toBeInTheDocument()

  await waitFor(() => expect(screen.getByText(/Problem 1/i)).toBeInTheDocument())

  expect(screen.getByText(/Test/)).toBeInTheDocument()
})
