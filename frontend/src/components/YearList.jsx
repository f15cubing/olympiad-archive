import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function YearList() {
  const isAdmin = true; // TODO: Replace with real auth system later

  const { compId } = useParams();
  const navigate = useNavigate();
  const [years, setYears] = useState([]);
  const [compName, setCompName] = useState("");
  const [showYearForm, setShowYearForm] = useState(false);
  const [newYear, setNewYear] = useState(new Date().getFullYear());

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
        const filtered = res.data.filter(p => parseInt(p.competition_id) === parseInt(compId));
        const uniqueYears = [...new Set(filtered.map(p => parseInt(p.year)))].sort((a, b) => b - a);
        setYears(uniqueYears);
      });
  }, [compId]);

  const handleDeleteYear = async (yearToDelete) => {
    if (!window.confirm(`Are you sure you want to delete all problems from ${yearToDelete}?`)) return;
    try {
      // Find all problems in this year and delete them
      const allProblems = await axios.get('http://localhost:8000/problems/');
      const problemsToDelete = allProblems.data.filter(
        p => p.competition_id === parseInt(compId) && p.year === yearToDelete
      );

      for (const problem of problemsToDelete) {
        await axios.delete(`http://localhost:8000/problems/${problem.id}/`);
      }

      setYears(years.filter(y => y !== yearToDelete));
    } catch (err) {
      console.error("Error deleting year:", err);
      alert('Failed to delete year');
    }
  };

  const handleAddYear = (e) => {
    e.preventDefault();
    // Navigate to the problem list for this year (where admin can add first problem)
    navigate(`/competition/${compId}/${newYear}`);
    setShowYearForm(false);
    setNewYear(new Date().getFullYear());
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/" className="text-blue-600 hover:underline mb-6 inline-block">← All Competitions</Link>
      <h1 className="text-3xl font-bold mb-8 text-slate-800">{compName}</h1>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {years.map(year => (
          <div key={year} className="relative group">
            <Link to={`/competition/${compId}/${year}`}
              className="block p-4 bg-white text-center rounded-lg border border-slate-200 hover:bg-blue-50 hover:border-blue-300 font-medium transition-colors">
              {year}
            </Link>
            {isAdmin && (
              <button
                onClick={() => handleDeleteYear(year)}
                className="absolute top-1 right-1 bg-red-100 hover:bg-red-200 text-red-700 font-bold py-0.5 px-1.5 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
