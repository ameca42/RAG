import { useState, useEffect } from 'react';
import type { Article } from './types/index';
import { fetchFeed, searchArticles } from './api';
import { NavBar } from './components/NavBar';
import { ArticleCard } from './components/ArticleCard';
import { ArticleModal } from './components/ArticleModal';

function App() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(null);
  const [searchMode, setSearchMode] = useState(false);

  useEffect(() => {
    loadArticles();
  }, [selectedTopic]);

  const loadArticles = async () => {
    setLoading(true);
    setSearchMode(false);
    try {
      const data = await fetchFeed(1, 50, selectedTopic || undefined);
      setArticles(data.articles);
    } catch (error) {
      console.error('Failed to load articles:', error);
      // Use mock data if API fails
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (query: string) => {
    setLoading(true);
    setSearchMode(true);
    try {
      const data = await searchArticles(query, 30);
      setArticles(data.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTopicChange = (topic: string | null) => {
    setSelectedTopic(topic);
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 antialiased">
      <NavBar
        selectedTopic={selectedTopic}
        onTopicChange={handleTopicChange}
        onSearch={handleSearch}
      />

      <main className="max-w-7xl mx-auto px-4 py-6">
        {searchMode && (
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm text-gray-500">
              搜索结果: {articles.length} 篇文章
            </span>
            <button
              onClick={loadArticles}
              className="text-sm text-orange-500 hover:text-orange-600"
            >
              清除搜索
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
          </div>
        ) : articles.length > 0 ? (
          <div className="masonry-grid">
            {articles.map((article) => (
              <ArticleCard
                key={article.item_id}
                article={article}
                onClick={() => setSelectedArticleId(article.item_id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-gray-500">暂无文章</p>
            <p className="text-sm text-gray-400 mt-2">
              请确保后端服务已启动并且有数据
            </p>
          </div>
        )}
      </main>

      {/* Article Modal */}
      {selectedArticleId && (
        <ArticleModal
          articleId={selectedArticleId}
          onClose={() => setSelectedArticleId(null)}
        />
      )}
    </div>
  );
}

export default App;
