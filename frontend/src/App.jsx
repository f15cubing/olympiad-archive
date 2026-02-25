import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css'
import ProblemList from './components/ProblemList'
import ProblemDetail from './components/ProblemDetail';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/" element={<ProblemList />} />
          <Route path="/problem/:id" element={<ProblemDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App
