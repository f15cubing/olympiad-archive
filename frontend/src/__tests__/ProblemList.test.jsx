import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProblemList from '../components/ProblemList'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const problemsData = [
  { id: 1, competition_id: 5, year: 2022, problem_number: 1, statement: 'Find $x$ such that $x^2 = 4$', author: 'John Doe' },
  { id: 2, competition_id: 5, year: 2022, problem_number: 2, statement: 'Prove that...', author: null },
]

const server = setupServer(
  rest.get('http://localhost:8000/problems/', (req, res, ctx) => {
    return res(ctx.json(problemsData))
  }),
  rest.post('http://localhost:8000/problems/', (req, res, ctx) =>
    res(ctx.json({ id: 3, competition_id: 5, year: 2022, problem_number: 3, statement: 'New problem', author: 'Test Author' }))
  ),
  rest.delete('http://localhost:8000/problems/:id/', (req, res, ctx) => res(ctx.json({ message: 'Deleted' })))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders list of problems for given competition and year', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  expect(screen.getByText(/Loading problems/i)).toBeInTheDocument()

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  expect(screen.getByText(/Problem 2/)).toBeInTheDocument()
})

test('displays problem authors when available', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/John Doe/)).toBeInTheDocument())
})

test('shows "Add Problem" button for admins', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  const addButton = screen.getByText(/Add Problem/)
  expect(addButton).toBeInTheDocument()
})

test('opens form when "Add Problem" is clicked', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  const addButton = screen.getByText(/Add Problem/)
  await user.click(addButton)

  expect(screen.getByLabelText(/Problem Number/)).toBeInTheDocument()
  expect(screen.getByLabelText(/Problem Statement/)).toBeInTheDocument()
  expect(screen.getByLabelText(/Problem Author/)).toBeInTheDocument()
})

test('can fill and submit the problem form', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  
  const addButton = screen.getByText(/Add Problem/)
  await user.click(addButton)

  const numberInput = screen.getByPlaceholderText('1')
  const statementInput = screen.getByPlaceholderText(/Problem statement/)
  const authorInput = screen.getByPlaceholderText(/Author name/)

  await user.type(numberInput, '3')
  await user.type(statementInput, 'Test problem statement')
  await user.type(authorInput, 'Test Author')

  const submitButton = screen.getByText(/Save Problem/)
  await user.click(submitButton)

  await waitFor(() => expect(screen.queryByLabelText(/Problem Number/)).not.toBeInTheDocument())
})

test('shows delete button for each problem', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  const deleteButtons = screen.getAllByText(/Delete/)
  expect(deleteButtons.length).toBeGreaterThan(0)
})

test('back button links to correct year list', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5/2022']}>
      <Routes>
        <Route path="/competition/:compId/:year" element={<ProblemList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Problem 1/)).toBeInTheDocument())
  const backButton = screen.getByText(/Back to Years/)
  expect(backButton).toBeInTheDocument()
  expect(backButton.closest('a')).toHaveAttribute('href', '/competition/5')
})
