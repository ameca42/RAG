import { useState, useEffect } from 'react';
import type { TopicCount } from '../types/index';
import { fetchTopics } from '../api';

interface NavBarProps {
  selectedTopic: string | null;
  onTopicChange: (topic: string | null) => void;
  onSearch: (query: string) => void;
}

export function NavBar({ selectedTopic, onTopicChange, onSearch }: NavBarProps) {
  const [topics, setTopics] = useState<TopicCount[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    loadTopics();
  }, []);

  const loadTopics = async () => {
    try {
      const data = await fetchTopics();
      setTopics(data.topics);
    } catch (error) {
      console.error('Failed to load topics:', error);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  return (
    <nav className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-100">
      {/* Top bar */}
      <div className="px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 text-orange-500">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path>
          </svg>
          <h1 className="text-xl font-bold tracking-tight">Hacker News</h1>
        </div>

        {/* Search toggle */}
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="p-2 text-gray-500 hover:text-gray-700"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search bar */}
      {showSearch && (
        <div className="px-4 pb-3">
          <form onSubmit={handleSearch} className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文章..."
              className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              autoFocus
            />
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </form>
        </div>
      )}

      {/* Topic tabs */}
      <div className="px-4 pb-2 overflow-x-auto">
        <div className="flex space-x-4 text-sm font-medium text-gray-500">
          <button
            onClick={() => onTopicChange(null)}
            className={`whitespace-nowrap pb-2 transition ${
              selectedTopic === null
                ? 'text-gray-900 border-b-2 border-orange-500'
                : 'hover:text-gray-900'
            }`}
          >
            全部
          </button>
          {topics.map((topic) => (
            <button
              key={topic.topic}
              onClick={() => onTopicChange(topic.topic)}
              className={`whitespace-nowrap pb-2 transition ${
                selectedTopic === topic.topic
                  ? 'text-gray-900 border-b-2 border-orange-500'
                  : 'hover:text-gray-900'
              }`}
            >
              {topic.topic} ({topic.count})
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
