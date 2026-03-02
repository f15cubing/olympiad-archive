import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

export default function YearList() {
  const { compId } = useParams();
  const [years, setYears] = useState([]);
  const [compName, setCompName] = useState("");

  useEffect(() => {
    // 1. Get competition name for the heading
    axios.get(`http://localhost:8000/competitions/`)
      .then(res => {
        const current = res.data.find(c => c.id === parseInt(compId));
        if (current) setCompName(current.name);
      });

    // 2. Fetch problems to extract unique years for this competition
    axios.get(`http://localhost:8000/problems/`)
      .then(res => {
        const filtered = res.data.filter(p => p.competition_id === parseInt(compId));
        const uniqueYears = [...new Set(filtered.map(p => p.year))].sort((a, b) => b - a);
        setYears(uniqueYears);
      });
  }, [compId]);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/" className="text-blue-600 hover:underline mb-6 inline-block">← All Competitions</Link>
      <h1 className="text-3xl font-bold mb-8 text-slate-800">{compName}</h1>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {years.map(year => (
          <Link key={year} to={`/competition/${compId}/${year}`}
            className="p-4 bg-white text-center rounded-lg border border-slate-200 hover:bg-blue-50 hover:border-blue-300 font-medium transition-colors">
            {year}
          </Link>
        ))}
      </div>
    </div>
  );
}
