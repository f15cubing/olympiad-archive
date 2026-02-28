import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import { useParams, Link } from 'react-router-dom'; // Combined imports

export default function ProblemList() {
  const { compId, year } = useParams();
  const [problems, setProblems] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/problems/')
      .then(res => {
        const filtered = res.data.filter(p =>
            p.competition_id === parseInt(compId) && p.year === parseInt(year)
        );
        setProblems(filtered);
      })
      .catch(err => console.error(err));
  }, [compId, year]);

  const renderStatement = (text) => {
    return text.split(/(\$.*?\$)/g).map((part, index) => {
      if (part.startsWith('$') && part.endsWith('$')) {
        return <InlineMath key={index} math={part.slice(1, -1)} />;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to={`/competition/${compId}`} className="text-blue-600 hover:underline mb-6 inline-block">
        ← Back to Years
      </Link>
      <h1 className="text-3xl font-bold mb-8 text-slate-800">Problems</h1>
      <div className="space-y-4">
        {problems.map(p => (
          <Link key={p.id} to={`/problem/${p.id}`} className="block p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors">
            <div className="flex justify-between text-sm font-medium text-blue-600 mb-2">
              <span>Problem {p.problem_number}</span>
              <span className="text-slate-400">{p.year}</span>
            </div>
            <div className="text-slate-700 leading-relaxed">
              {renderStatement(p.statement)}
            </div>
          </Link>
        ))}
        {problems.length === 0 && (
          <p className="text-slate-500 italic">No problems found for this selection.</p>
        )}
      </div>
    </div>
  );
}
