import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CompetitionList from '../components/CompetitionList'
import { MemoryRouter } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const competitions = [
  { id: 1, name: 'IMO', country: 'International', description: 'International Math Olympiad' },
  { id: 2, name: 'USAMO', country: 'USA', description: 'USA Math Olympiad' }
]

const server = setupServer(
  rest.get('http://localhost:8000/competitions/', (req, res, ctx) => res(ctx.json(competitions))),
  rest.post('http://localhost:8000/competitions/', (req, res, ctx) =>
    res(ctx.json({ id: 3, name: 'IMO 2023', country: 'International', description: 'New competition' }))
  ),
  rest.delete('http://localhost:8000/competitions/:id/', (req, res, ctx) => res(ctx.json({ message: 'Deleted' })))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders competition list with names and countries', async () => {
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/IMO/)).toBeInTheDocument())
  expect(screen.getByText(/USAMO/)).toBeInTheDocument()
  expect(screen.getAllByText(/International/).length).toBeGreaterThan(0)
  expect(screen.getByText('USA')).toBeInTheDocument()
})

test('displays competition descriptions', async () => {
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/International Math Olympiad/)).toBeInTheDocument())
  expect(screen.getByText(/USA Math Olympiad/)).toBeInTheDocument()
})

test('shows "Add Competition" button for admins', async () => {
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  const addButton = screen.getByText(/Add Competition/)
  expect(addButton).toBeInTheDocument()
})

test('opens form when "Add Competition" is clicked', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  const addButton = screen.getByText(/Add Competition/)
  await user.click(addButton)

  expect(screen.getByLabelText(/Competition Name/)).toBeInTheDocument()
  expect(screen.getByLabelText(/Description/)).toBeInTheDocument()
  expect(screen.getByLabelText(/Country/)).toBeInTheDocument()
})

test('can fill and submit the form with country field', async () => {
  const user = userEvent.setup()
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  const addButton = screen.getByText(/Add Competition/)
  await user.click(addButton)

  const nameInput = screen.getByPlaceholderText(/IMO 2023/)
  const countryInput = screen.getByPlaceholderText(/International, USA/)
  const descriptionInput = screen.getByPlaceholderText(/Optional description/)

  await user.type(nameInput, 'Test Competition')
  await user.type(countryInput, 'Test Country')
  await user.type(descriptionInput, 'Test Description')

  const submitButton = screen.getByText(/Save Competition/)
  await user.click(submitButton)

  await waitFor(() => expect(screen.queryByLabelText(/Competition Name/)).not.toBeInTheDocument())
})

test('shows delete button for each competition', async () => {
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/IMO/)).toBeInTheDocument())
  const deleteButtons = screen.getAllByText(/Delete/)
  expect(deleteButtons.length).toBeGreaterThan(0)
})

test('handles API errors gracefully', async () => {
  server.use(
    rest.get('http://localhost:8000/competitions/', (req, res, ctx) =>
      res(ctx.status(500), ctx.json({ error: 'Server error' }))
    )
  )

  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Could not connect to backend/)).toBeInTheDocument())
})
