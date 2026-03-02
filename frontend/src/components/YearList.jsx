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
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-slate-800">{compName}</h1>
        {isAdmin && (
          <button
            onClick={() => setShowYearForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            + Add Year
          </button>
        )}
      </div>

      {showYearForm && (
        <div className="mb-6 p-6 bg-slate-50 border border-slate-200 rounded-xl">
          <h2 className="text-lg font-semibold mb-4 text-slate-800">Add New Year</h2>
          <form onSubmit={handleAddYear} className="space-y-4">
            <div>
              <label htmlFor="year-input" className="block text-sm font-medium text-slate-700 mb-1">
                Year *
              </label>
              <input
                id="year-input"
                type="number"
                required
                value={newYear}
                onChange={(e) => setNewYear(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={new Date().getFullYear()}
              />
              <p className="text-xs text-slate-500 mt-1">You'll be taken to add problems for this year</p>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Continue to Add Problems
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowYearForm(false);
                  setNewYear(new Date().getFullYear());
                }}
                className="bg-slate-300 hover:bg-slate-400 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

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
