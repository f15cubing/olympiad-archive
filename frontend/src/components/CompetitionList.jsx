import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function CompetitionList() {
  const [competitions, setCompetitions] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Ensure the URL is correct (plural 'competitions')
    axios.get('http://localhost:8000/competitions/')
      .then(res => setCompetitions(res.data))
      .catch(err => {
        console.error("API Error:", err);
        setError("Could not connect to backend");
      });
  }, []);

  if (error) return <div className="p-8 text-red-500">{error}</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">Competitions</h1>
      {competitions.length === 0 ? (
        <p>No competitions found in database.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitions.map(c => (
            <Link key={c.id} to={`/competition/${c.id}`}
              className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-400 transition-all">
              <h2 className="text-xl font-semibold text-blue-600">{c.name}</h2>
              <p className="text-slate-500">{c.country || 'International'}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
