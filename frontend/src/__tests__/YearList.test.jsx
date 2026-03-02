import { render, screen, waitFor } from '@testing-library/react'
import YearList from '../components/YearList'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

// YearList is a simple component that shows years for a competition; we can
// render it with sample props instead of network mocking.

test('renders years list', async () => {
  render(
    <MemoryRouter>
      <YearList years={[2020, 2021, 2022]} compId={5} />
    </MemoryRouter>
  )

  expect(screen.getByText(/2020/)).toBeInTheDocument()
  expect(screen.getByText(/2022/)).toBeInTheDocument()
})
