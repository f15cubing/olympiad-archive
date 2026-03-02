import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import YearList from '../components/YearList'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  rest.get('http://localhost:8000/competitions/', (req, res, ctx) =>
    res(ctx.json([
      { id: 5, name: 'AMC', country: 'USA' },
      { id: 6, name: 'IMO', country: 'International' }
    ]))
  ),
  rest.get('http://localhost:8000/problems/', (req, res, ctx) =>
    res(ctx.json([
      { id: 1, competition_id: 5, year: 2020, problem_number: 1, statement: 'Problem' },
      { id: 2, competition_id: 5, year: 2021, problem_number: 1, statement: 'Problem' },
      { id: 3, competition_id: 5, year: 2022, problem_number: 1, statement: 'Problem' },
    ]))
  ),
  rest.delete('http://localhost:8000/problems/:id/', (req, res, ctx) => res(ctx.json({ message: 'Deleted' })))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders years list for a competition', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())
  expect(screen.getByText(/2021/)).toBeInTheDocument()
  expect(screen.getByText(/2022/)).toBeInTheDocument()
})

test('displays competition name in heading', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/AMC/)).toBeInTheDocument())
})

test('shows "Add Year" button for admins', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())
  const addButton = screen.getByText(/Add Year/)
  expect(addButton).toBeInTheDocument()
})

test('opens year form when "Add Year" is clicked', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())
  const addButton = screen.getByText(/Add Year/)
  await user.click(addButton)

  expect(screen.getByLabelText(/Year/)).toBeInTheDocument()
  expect(screen.getByText(/Continue to Add Problems/)).toBeInTheDocument()
})

test('can fill and submit the year form', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())

  const addButton = screen.getByText(/Add Year/)
  await user.click(addButton)

  const yearInput = screen.getByLabelText(/Year/)
  await user.clear(yearInput)
  await user.type(yearInput, '2025')

  const submitButton = screen.getByText(/Continue to Add Problems/)
  await user.click(submitButton)

  // After submit, form should close
  await waitFor(() => expect(screen.queryByLabelText(/Year/)).not.toBeInTheDocument())
})

test('back button links to competitions list', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())
  const backButton = screen.getByText(/All Competitions/)
  expect(backButton).toBeInTheDocument()
  expect(backButton.closest('a')).toHaveAttribute('href', '/')
})

test('shows delete button on year hover for admins', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())

  const yearCard = screen.getByText('2020').closest('div')
  await user.hover(yearCard)

  const deleteButton = yearCard.querySelector('button')
  expect(deleteButton).toBeInTheDocument()
})

test('year cards link to problem list', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())

  const year2020Link = screen.getByText('2020').closest('a')
  expect(year2020Link).toHaveAttribute('href', '/competition/5/2020')

  const year2021Link = screen.getByText('2021').closest('a')
  expect(year2021Link).toHaveAttribute('href', '/competition/5/2021')
})
