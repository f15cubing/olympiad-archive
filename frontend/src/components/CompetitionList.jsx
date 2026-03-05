import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';

export default function CompetitionList() {
  const isAdmin = true; // TODO: Replace with real auth system later
  const navigate = useNavigate();

  const [competitions, setCompetitions] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', country: '' });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Ensure the URL is correct (plural 'competitions')
    axios.get('http://localhost:8000/competitions/')
      .then(res => setCompetitions(res.data))
      .catch(err => {
        console.error("API Error:", err);
        setError("Could not connect to backend");
      });
  }, []);

  const handleAddCompetition = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await axios.post('http://localhost:8000/competitions/', formData);
      setCompetitions([...competitions, res.data]);
      setFormData({ name: '', description: '', country: '' });
      setShowForm(false);
      // Navigate to the new competition's year list to add years/problems
      navigate(`/competition/${res.data.id}`);
    } catch (err) {
      console.error("Error adding competition:", err);
      alert('Failed to add competition');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteCompetition = async (id) => {
    if (!window.confirm('Are you sure you want to delete this competition?')) return;
    try {
      await axios.delete(`http://localhost:8000/competitions/${id}/`);
      setCompetitions(competitions.filter(c => c.id !== id));
    } catch (err) {
      console.error("Error deleting competition:", err);
      alert('Failed to delete competition');
    }
  };

  if (error) return <div className="p-8 text-red-500">{error}</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Competitions</h1>
        <div className="flex gap-4">
          <Link to="/search" className="text-blue-600 hover:underline">Search Problems</Link>
          {isAdmin && (
            <button
              onClick={() => setShowForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              + Add Competition
            </button>
          )}
        </div>
      </div>

      {showForm && (
        <div className="mb-6 p-6 bg-slate-50 border border-slate-200 rounded-xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-800">Add New Competition</h2>
          <form onSubmit={handleAddCompetition} className="space-y-4">
            <div>
              <label htmlFor="comp-name" className="block text-sm font-medium text-slate-700 mb-1">
                Competition Name *
              </label>
              <input
                id = "comp-name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., IMO 2023"
              />
            </div>
            <div>
              <label htmlFor="comp-description" className="block text-sm font-medium text-slate-700 mb-1">
                Description
              </label>
              <textarea
                id="comp-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional description"
                rows="3"
              />
            </div>
            <div>
              <label htmlFor="comp-country" className="block text-sm font-medium text-slate-700 mb-1">
                Country
              </label>
              <input
                id = "comp-country"
                type="text"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., International, USA"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {submitting ? 'Saving...' : 'Save Competition'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormData({ name: '', description: '', country: '' });
                }}
                className="bg-slate-300 hover:bg-slate-400 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {competitions.length === 0 ? (
        <p>No competitions found in database.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitions.map(c => (
            <div key={c.id} className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-400 transition-all">
              <Link to={`/competition/${c.id}`}
                className="block group">
                <h2 className="text-xl font-semibold text-blue-600 group-hover:underline">{c.name}</h2>
                <p className="text-slate-500">{c.country || 'International'}</p>
                {c.description && <p className="text-slate-600 text-sm mt-2">{c.description}</p>}
              </Link>
              {isAdmin && (
                <button
                  onClick={() => handleDeleteCompetition(c.id)}
                  className="mt-4 text-sm bg-red-100 hover:bg-red-200 text-red-700 font-medium py-1 px-3 rounded transition-colors"
                >
                  Delete
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
