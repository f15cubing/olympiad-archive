import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css'

import ProblemList from './components/ProblemList'
import ProblemDetail from './components/ProblemDetail';
import CompetitionList from './components/CompetitionList';
import YearList from './components/YearList';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/" element={<CompetitionList />} />
          <Route path="/competition/:compId" element={<YearList />} />
          <Route path="/competition/:compId/:year" element={<ProblemList />} />
          <Route path="/problem/:id" element={<ProblemDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App
