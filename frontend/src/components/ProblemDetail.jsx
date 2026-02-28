import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';

export default function ProblemDetail() {
  const { id } = useParams();
  const [problem, setProblem] = useState(null);

  useEffect(() => {
    axios.get(`http://localhost:8000/problems/${id}`)
      .then(res => setProblem(res.data))
      .catch(err => console.error("Error loading problem:", err));
  }, [id]);

  const renderStatement = (text) => {
      return text.split(/(\$.*?\$)/g).map((part, index) => {
        if (part.startsWith('$') && part.endsWith('$')) {
          return <InlineMath key={index} math={part.slice(1, -1)} />;
        }
        return <span key={index}>{part}</span>;
      });
    };

  if (!problem) return <div className="p-8 text-center">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Dynamic Back Button based on current problem's data */}
      <Link
        to={`/competition/${problem.competition_id}/${problem.year}`}
        className="text-blue-600 hover:underline mb-6 inline-block"
      >
        ← Back to List
      </Link>

      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 mb-6">
        <h1 className="text-2xl font-bold mb-4 text-slate-800">
          Problem {problem.problem_number} ({problem.year})
        </h1>

        {/* Rendered Problem Statement */}
        <div className="text-lg text-slate-700 leading-relaxed border-b pb-6 mb-6">
          {renderStatement(problem.statement)}
        </div>

        {/* Display Solutions */}
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4 text-slate-800">Solutions</h2>
          {problem.solutions && problem.solutions.length > 0 ? (
            problem.solutions.map((sol) => (
              <div key={sol.id} className="bg-slate-50 p-6 rounded-lg border border-slate-200 mb-4">
                <p className="text-sm font-medium text-blue-600 mb-2">Author: {sol.author}</p>
                <div className="text-slate-800 leading-relaxed">
                  {/* Using renderStatement here too for solutions with math */}
                  {renderStatement(sol.content)}
                </div>
              </div>
            ))
          ) : (
            <p className="text-slate-500 italic">No solutions added yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
