import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';
import { Link } from 'react-router-dom';

export default function Search() {
  const [query, setQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [allTags, setAllTags] = useState([]);
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    axios.get('http://localhost:8000/tags/').then(res => setAllTags(res.data));
  }, []);

  const handleSearch = async () => {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (selectedTag) params.append('tag', selectedTag);
    const res = await axios.get(`http://localhost:8000/problems/search?${params}`);
    setResults(res.data);
    setSearched(true);
  };

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
      <Link to="/" className="text-blue-600 hover:underline mb-6 inline-block">
        ← Back to Competitions
      </Link>
      <h1 className="text-3xl font-bold text-slate-800 mb-6">Search Problems</h1>
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Keyword Search
            </label>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search in problem statements..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Filter by Tag
            </label>
            <select
              value={selectedTag}
              onChange={e => setSelectedTag(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All tags</option>
              {allTags.map(t => <option key={t.id} value={t.name}>{t.name}</option>)}
            </select>
          </div>
          <button
            onClick={handleSearch}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Search
          </button>
        </div>
      </div>
      {searched && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Results ({results.length})</h2>
          <div className="space-y-4">
            {results.map(p => (
              <div key={p.id} className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:border-blue-300 transition-colors">
                <Link to={`/problem/${p.id}`} className="block group">
                  <div className="flex justify-between text-sm font-medium text-blue-600 mb-2">
                    <span>Problem {p.problem_number} ({p.year})</span>
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
              </div>
            ))}
            {results.length === 0 && (
              <p className="text-slate-500 italic">No problems found.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
