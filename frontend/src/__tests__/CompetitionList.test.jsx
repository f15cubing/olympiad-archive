import { render, screen, waitFor } from '@testing-library/react'
import CompetitionList from '../components/CompetitionList'
import { MemoryRouter } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const competitions = [{ id: 1, name: 'IMO' }, { id: 2, name: 'USAMO' }]

const server = setupServer(
  rest.get('http://localhost:8000/competitions/', (req, res, ctx) => res(ctx.json(competitions)))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders competitions', async () => {
  render(
    <MemoryRouter>
      <CompetitionList />
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/IMO/)).toBeInTheDocument())
  expect(screen.getByText(/USAMO/)).toBeInTheDocument()
})
