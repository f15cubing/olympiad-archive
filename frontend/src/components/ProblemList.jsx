import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

export default function ProblemList() {
  const [problems, setProblems] = useState([]);

  useEffect(() => {
    // Fetch from your FastAPI endpoint
    axios.get('http://localhost:8000/problems/')
      .then(res => setProblems(res.data))
      .catch(err => console.error("Connection failed:", err));
  }, []);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">Olympiad Archive</h1>
      <div className="space-y-4">
        {problems.map(p => (
          <div key={p.id} className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
            <div className="flex justify-between text-sm font-medium text-blue-600 mb-2">
              <span>Problem {p.problem_number}</span>
              <span className="text-slate-400">{p.year}</span>
            </div>
            <div className="text-slate-700 leading-relaxed">
              <InlineMath math={p.statement} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
