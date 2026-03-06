import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import { useParams, Link } from 'react-router-dom'; // Combined imports

export default function ProblemList() {
  const isAdmin = true; // TODO: Replace with real auth system later

  const { compId, year } = useParams();
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    problem_number: '',
    year: year ? parseInt(year) : '',
    statement: '',
    author: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [allTags, setAllTags] = useState([]);
  const [selectedTagIds, setSelectedTagIds] = useState([]);
  const [newTagName, setNewTagName] = useState('');

  useEffect(() => {
    axios.get('http://localhost:8000/problems/')
      .then(res => {
        const filtered = res.data.filter(p =>
            parseInt(p.competition_id) === parseInt(compId) && parseInt(p.year) === parseInt(year)
        );
        setProblems(filtered);
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [compId, year]);

  useEffect(() => {
    axios.get('http://localhost:8000/tags/').then(res => setAllTags(res.data));
  }, []);

  const handleAddProblem = async (e) => {
    e.preventDefault();

    // Validate problem_number
    const probNum = parseInt(formData.problem_number);
    if (!formData.problem_number || isNaN(probNum) || probNum <= 0) {
      alert('Please enter a valid problem number (must be >= 1)');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        problem_number: probNum,
        year: parseInt(formData.year),
        statement: formData.statement,
        author: formData.author || null,
        competition_id: parseInt(compId),
        tag_ids: selectedTagIds
      };
      const res = await axios.post('http://localhost:8000/problems/', payload);
      setProblems([...problems, res.data]);
      setFormData({
        problem_number: '',
        year: year ? parseInt(year) : '',
        statement: '',
        author: ''
      });
      setShowForm(false);
    } catch (err) {
      console.error("Error adding problem:", err);
      alert('Failed to add problem');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProblem = async (id) => {
    if (!window.confirm('Are you sure you want to delete this problem?')) return;
    try {
      await axios.delete(`http://localhost:8000/problems/${id}/`);
      setProblems(problems.filter(p => p.id !== id));
    } catch (err) {
      console.error("Error deleting problem:", err);
      alert('Failed to delete problem');
    }
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim()) return;
    try {
      const res = await axios.post('http://localhost:8000/tags/', { name: newTagName });
      setAllTags([...allTags, res.data]);
      setSelectedTagIds([...selectedTagIds, res.data.id]);
      setNewTagName('');
    } catch (err) {
      console.error("Error creating tag:", err);
      alert('Failed to create tag');
    }
  };

  const renderStatement = (text) => {
    return text.split(/(\$.*?\$)/g).map((part, index) => {
      if (part.startsWith('$') && part.endsWith('$')) {
        return <InlineMath key={index} math={part.slice(1, -1)} />;
      }
      return <span key={index}>{part}</span>;
    });
  };

  if (loading) return <p>Loading problems...</p>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to={`/competition/${compId}`} className="text-blue-600 hover:underline mb-6 inline-block">
        ← Back to Years
      </Link>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Problems</h1>
        {isAdmin && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            + Add Problem
          </button>
        )}
      </div>

      {showForm && (
        <div className="mb-6 p-6 bg-slate-50 border border-slate-200 rounded-xl">
          <h2 className="text-xl font-semibold mb-4 text-slate-800">Add New Problem</h2>
          <form onSubmit={handleAddProblem} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="prob-number" className="block text-sm font-medium text-slate-700 mb-1">
                  Problem Number *
                </label>
                <input
                  id="prob-number"
                  type="number"
                  required
                  value={formData.problem_number}
                  onChange={(e) => setFormData({ ...formData, problem_number: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="1"
                />
              </div>
              <div>
                <label htmlFor="prob-year" className="block text-sm font-medium text-slate-700 mb-1">
                  Year *
                </label>
                <input
                  id="prob-year"
                  type="number"
                  required
                  value={formData.year}
                  onChange={(e) => setFormData({ ...formData, year: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="2023"
                />
              </div>
            </div>
            <div>
              <label htmlFor="prob-statement" className="block text-sm font-medium text-slate-700 mb-1">
                Problem Statement *
              </label>
              <textarea
                id="prob-statement"
                required
                value={formData.statement}
                onChange={(e) => setFormData({ ...formData, statement: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Problem statement (supports LaTeX in $ delimiters)"
                rows="6"
              />
            </div>
            <div>
              <label htmlFor="prob-author" className="block text-sm font-medium text-slate-700 mb-1">
                Problem Author
              </label>
              <input
                id="prob-author"
                type="text"
                value={formData.author}
                onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Author name (optional)"
              />
            </div>
            <div>
              <label htmlFor="prob-tags" className="block text-sm font-medium text-slate-700 mb-1">
                Tags
              </label>
              <div className="flex flex-wrap gap-2">
                {allTags.map(tag => (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => setSelectedTagIds(prev =>
                      prev.includes(tag.id) ? prev.filter(id => id !== tag.id) : [...prev, tag.id]
                    )}
                    className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                      selectedTagIds.includes(tag.id)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'
                    }`}
                  >
                    {tag.name}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  placeholder="New tag name"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  className="flex-1 px-3 py-1 border border-slate-300 rounded text-sm"
                />
                <button
                  type="button"
                  onClick={handleCreateTag}
                  className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm"
                >
                  Create Tag
                </button>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {submitting ? 'Saving...' : 'Save Problem'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormData({
                    problem_number: '',
                    year: year ? parseInt(year) : '',
                    statement: '',
                    author: ''
                  });
                  setSelectedTagIds([]);
                  setNewTagName('');
                }}
                className="bg-slate-300 hover:bg-slate-400 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-4">
        {problems.map(p => (
          <div key={p.id} className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors">
            <Link to={`/problem/${p.id}`} className="block group">
              <div className="flex justify-between text-sm font-medium text-blue-600 mb-2">
                <span>Problem {p.problem_number}</span>
                <div className="flex gap-2 items-center">
                  {p.ai_metadata && <span className="bg-purple-100 text-purple-700 text-xs font-semibold px-2 py-1 rounded-full">✨ AI-Tagged</span>}
                  <span className="text-slate-400">{p.year}</span>
                </div>
              </div>
              {p.author && <p className="text-xs text-slate-500 mb-2">Author: {p.author}</p>}
              <div className="text-slate-700 leading-relaxed group-hover:text-blue-600">
                {renderStatement(p.statement)}
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
                {p.tags?.map(tag => (
                  <span key={tag.id} className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded-full">
                    {tag.name}
                  </span>
                ))}
              </div>
            </Link>
            {isAdmin && (
              <button
                onClick={() => handleDeleteProblem(p.id)}
                className="mt-4 text-sm bg-red-100 hover:bg-red-200 text-red-700 font-medium py-1 px-3 rounded transition-colors"
              >
                Delete
              </button>
            )}
          </div>
        ))}
        {problems.length === 0 && (
          <p className="text-slate-500 italic">No problems found for this selection.</p>
        )}
      </div>
    </div>
  );
}
