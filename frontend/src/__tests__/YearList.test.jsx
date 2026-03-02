import { render, screen, waitFor } from '@testing-library/react'
import YearList from '../components/YearList'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  rest.get('http://localhost:8000/competitions/', (req, res, ctx) =>
    res(ctx.json([{ id: 5, name: 'AMC' }]))
  ),
  rest.get('http://localhost:8000/problems/', (req, res, ctx) =>
    res(ctx.json([
      { id: 1, competition_id: 5, year: 2020 },
      { id: 2, competition_id: 5, year: 2022 },
    ]))
  )
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('renders years list', async () => {
  render(
    <MemoryRouter initialEntries={['/competition/5']}>
      <Routes>
        <Route path="/competition/:compId" element={<YearList />} />
      </Routes>
    </MemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/2020/)).toBeInTheDocument())
  expect(screen.getByText(/2022/)).toBeInTheDocument()
})
