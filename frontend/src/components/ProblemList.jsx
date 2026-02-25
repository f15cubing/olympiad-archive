import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import { Link } from 'react-router-dom';

export default function ProblemList() {
  const [problems, setProblems] = useState([]);

  useEffect(() => {
    // Fetch from your FastAPI endpoint
    axios.get('http://localhost:8000/problems/')
      .then(res => setProblems(res.data))
      .catch(err => console.error("Connection failed:", err));
  }, []);

  const renderStatement = (text) => {
    return text.split(/(\$.*?\$)/g).map((part, index) => {
      if (part.startsWith('$') && part.endsWith('$')) {
        // Remove the $ signs and render as math
        return <InlineMath key={index} math={part.slice(1, -1)} />;
      }
      // Render as normal text
      return <span key={index}>{part}</span>;
    });
  };


  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">Olympiad Archive</h1>
      <div className="space-y-4">
        {problems.map(p => (
          <Link to={`/problem/${p.id}`} className="block p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors">
            <div className="flex justify-between text-sm font-medium text-blue-600 mb-2">
              <span>Problem {p.problem_number}</span>
              <span className="text-slate-400">{p.year}</span>
            </div>
            <div className="text-slate-700 leading-relaxed">
              {renderStatement(p.statement)}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
