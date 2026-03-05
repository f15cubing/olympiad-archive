import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';

export default function ProblemDetail() {
  const isAdmin = true; // TODO: Replace with real auth system later

  const { id } = useParams();
  const [problem, setProblem] = useState(null);
  const [allTags, setAllTags] = useState([]);
  const [showSolutionForm, setShowSolutionForm] = useState(false);
  const [showTagForm, setShowTagForm] = useState(false);
  const [solutionFormData, setSolutionFormData] = useState({
    content: '',
    author: ''
  });
  const [selectedTagIds, setSelectedTagIds] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    // Fetch problem and all available tags
    Promise.all([
      axios.get(`http://localhost:8000/problems/${id}`),
      axios.get('http://localhost:8000/tags/')
    ])
      .then(([problemRes, tagsRes]) => {
        setProblem(problemRes.data);
        setAllTags(tagsRes.data);
        setSelectedTagIds(problemRes.data.tags?.map(tag => tag.id) || []);
      })
      .catch(err => console.error("Error loading problem or tags:", err));
  }, [id]);

  const handleAddSolution = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        problem_id: parseInt(id),
        content: solutionFormData.content,
        author: solutionFormData.author || 'Official'
      };
      const res = await axios.post('http://localhost:8000/solutions/', payload);
      setProblem({
        ...problem,
        solutions: [...problem.solutions, res.data]
      });
      setSolutionFormData({ content: '', author: '' });
      setShowSolutionForm(false);
    } catch (err) {
      console.error("Error adding solution:", err);
      alert('Failed to add solution');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSolution = async (solutionId) => {
    if (!window.confirm('Are you sure you want to delete this solution?')) return;
    try {
      await axios.delete(`http://localhost:8000/solutions/${solutionId}/`);
      setProblem({
        ...problem,
        solutions: problem.solutions.filter(s => s.id !== solutionId)
      });
    } catch (err) {
      console.error("Error deleting solution:", err);
      alert('Failed to delete solution');
    }
  };

  const handleSaveTags = async () => {
    setSubmitting(true);
    try {
      const res = await axios.put(`http://localhost:8000/problems/${id}`, {
        year: problem.year,
        problem_number: problem.problem_number,
        statement: problem.statement,
        author: problem.author,
        difficulty: problem.difficulty,
        source_url: problem.source_url,
        competition_id: problem.competition_id,
        tag_ids: selectedTagIds
      });
      setProblem(res.data);
      setShowTagForm(false);
    } catch (err) {
      console.error("Error updating tags:", err);
      alert('Failed to update tags');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTagToggle = (tagId) => {
    setSelectedTagIds(prev =>
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

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
        {problem.author && (
          <p className="text-sm text-slate-500 mb-4">Author: {problem.author}</p>
        )}

        {/* Rendered Problem Statement */}
        <div className="text-lg text-slate-700 leading-relaxed border-b pb-6 mb-6">
          {renderStatement(problem.statement)}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mt-4 mb-6">
          {problem.tags?.map(tag => (
            <span key={tag.id} className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded-full">
              {tag.name}
            </span>
          ))}
        </div>

        {isAdmin && (
          <button
            onClick={() => {
              setShowTagForm(true);
              setSelectedTagIds(problem.tags?.map(tag => tag.id) || []);
            }}
            className="bg-amber-500 hover:bg-amber-600 text-white font-semibold py-2 px-4 rounded-lg transition-colors mb-6"
          >
            {problem.tags?.length > 0 ? '✎ Edit Tags' : '+ Add Tags'}
          </button>
        )}

        {/* Tag Edit Form */}
        {showTagForm && (
          <div className="mb-6 p-6 bg-slate-50 border border-slate-200 rounded-xl">
            <h3 className="text-lg font-semibold mb-4 text-slate-800">Manage Tags</h3>
            <div className="space-y-3 mb-4">
              {allTags.length > 0 ? (
                allTags.map(tag => (
                  <label key={tag.id} className="flex items-center cursor-pointer hover:bg-white p-2 rounded transition-colors">
                    <input
                      type="checkbox"
                      checked={selectedTagIds.includes(tag.id)}
                      onChange={() => handleTagToggle(tag.id)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="ml-3 text-slate-700">{tag.name}</span>
                  </label>
                ))
              ) : (
                <p className="text-slate-500 italic">No tags available. Create some first!</p>
              )}
            </div>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={handleSaveTags}
                disabled={submitting}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
              >
                {submitting ? 'Saving...' : 'Save Tags'}
              </button>
              <button
                type="button"
                onClick={() => setShowTagForm(false)}
                className="bg-slate-300 hover:bg-slate-400 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Display Solutions */}
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-slate-800">Solutions</h2>
            {isAdmin && (
              <button
                onClick={() => setShowSolutionForm(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-1 px-3 rounded text-sm transition-colors"
              >
                + Add Solution
              </button>
            )}
          </div>

          {showSolutionForm && (
            <div className="mb-6 p-6 bg-slate-50 border border-slate-200 rounded-xl">
              <h3 className="text-lg font-semibold mb-4 text-slate-800">Add New Solution</h3>
              <form onSubmit={handleAddSolution} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Solution Author
                  </label>
                  <input
                    type="text"
                    value={solutionFormData.author}
                    onChange={(e) => setSolutionFormData({ ...solutionFormData, author: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Author name (defaults to 'Official')"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Solution Content *
                  </label>
                  <textarea
                    required
                    value={solutionFormData.content}
                    onChange={(e) => setSolutionFormData({ ...solutionFormData, content: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Solution (supports LaTeX in $ delimiters)"
                    rows="6"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                  >
                    {submitting ? 'Saving...' : 'Save Solution'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowSolutionForm(false);
                      setSolutionFormData({ content: '', author: '' });
                    }}
                    className="bg-slate-300 hover:bg-slate-400 text-slate-700 font-medium py-2 px-4 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {problem.solutions && problem.solutions.length > 0 ? (
            problem.solutions.map((sol) => (
              <div key={sol.id} className="bg-slate-50 p-6 rounded-lg border border-slate-200 mb-4">
                <div className="flex justify-between items-start mb-2">
                  <p className="text-sm font-medium text-blue-600">Author: {sol.author}</p>
                  {isAdmin && (
                    <button
                      onClick={() => handleDeleteSolution(sol.id)}
                      className="text-sm bg-red-100 hover:bg-red-200 text-red-700 font-medium py-1 px-2 rounded transition-colors"
                    >
                      Delete
                    </button>
                  )}
                </div>
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
