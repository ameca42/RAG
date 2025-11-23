import { useState, useEffect } from 'react';
import type { Article, Comment, ChatMessage } from '../types/index';
import { fetchArticleDetail, chatWithArticle } from '../api';
import { AICopilot } from './AICopilot';

interface ArticleModalProps {
  articleId: number | null;
  onClose: () => void;
}

export function ArticleModal({ articleId, onClose }: ArticleModalProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (articleId) {
      loadArticle(articleId);
    }
  }, [articleId]);

  const loadArticle = async (id: number) => {
    setLoading(true);
    try {
      const data = await fetchArticleDetail(id);
      setArticle(data.article);
      setComments(data.comments);
    } catch (error) {
      console.error('Failed to load article:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async (message: string) => {
    if (!articleId) return;

    setChatHistory(prev => [...prev, { role: 'user', content: message }]);
    setChatLoading(true);

    try {
      const response = await chatWithArticle(articleId, message, chatHistory);
      setChatHistory(prev => [...prev, { role: 'assistant', content: response.response }]);
    } catch (error) {
      console.error('Chat failed:', error);
      setChatHistory(prev => [...prev, { role: 'assistant', content: '抱歉，AI 响应失败，请稍后重试。' }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (!articleId) return null;

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 transition-opacity"
      onClick={onClose}
    >
      <div
        className="fixed inset-2 md:inset-10 bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col md:flex-row"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Article Content Panel */}
        <div className="flex-1 overflow-y-auto p-8 bg-white">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
          ) : article ? (
            <>
              <span className="inline-block bg-blue-50 text-blue-600 text-xs font-bold px-2 py-1 rounded mb-4">
                {article.topic}
              </span>
              <h2 className="text-3xl font-bold mb-4 leading-tight">{article.title}</h2>
              <div className="flex items-center space-x-3 text-sm text-gray-500 mb-8">
                <span className="font-medium">{article.author}</span>
                <span>•</span>
                <span>{article.crawl_date}</span>
                <span>•</span>
                <span>{article.score} points</span>
              </div>
              <article className="prose prose-lg max-w-none">
                {article.content_summary ? (
                  <div className="whitespace-pre-wrap">{article.content_summary}</div>
                ) : (
                  <p className="text-gray-500">
                    No content available.
                    <a href={article.url} target="_blank" rel="noopener noreferrer" className="text-orange-500 ml-2">
                      View original →
                    </a>
                  </p>
                )}
              </article>
              {article.url && (
                <div className="mt-6">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-orange-500 hover:text-orange-600"
                  >
                    阅读原文 →
                  </a>
                </div>
              )}
            </>
          ) : (
            <p className="text-gray-500">Article not found</p>
          )}
        </div>

        {/* Comments Panel */}
        <div className="w-full md:w-[400px] bg-gray-50 border-l border-gray-100 flex flex-col relative">
          {/* Header */}
          <div className="sticky top-0 bg-gray-50/90 backdrop-blur z-10 p-4 border-b border-gray-100 flex justify-between items-center">
            <h3 className="font-bold text-lg">Comments ({comments.length})</h3>
            <button
              onClick={() => setShowAI(!showAI)}
              className="flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-2 rounded-full font-medium hover:shadow-md transition-all"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path fillRule="evenodd" d="M9 4.5a.75.75 0 01.721.544l.813 2.846a3.75 3.75 0 002.576 2.576l2.846.813a.75.75 0 010 1.442l-2.846.813a3.75 3.75 0 00-2.576 2.576l-.813 2.846a.75.75 0 01-1.442 0l-.813-2.846a3.75 3.75 0 00-2.576-2.576l-2.846-.813a.75.75 0 010-1.442l2.846-.813a3.75 3.75 0 002.576-2.576l.813-2.846A.75.75 0 019 4.5z" clipRule="evenodd" />
              </svg>
              <span>Ask AI</span>
            </button>
          </div>

          {/* Comments List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {comments.length > 0 ? (
              comments.map((comment) => (
                <CommentItem key={comment.id} comment={comment} />
              ))
            ) : article?.comments_summary ? (
              <div className="text-sm text-gray-600 whitespace-pre-wrap">
                {article.comments_summary}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No comments available</p>
            )}
          </div>

          {/* AI Copilot Sidebar */}
          {showAI && (
            <AICopilot
              messages={chatHistory}
              onSend={handleChat}
              onClose={() => setShowAI(false)}
              loading={chatLoading}
            />
          )}
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 bg-white/80 backdrop-blur p-2 rounded-full text-gray-600 hover:bg-white z-30"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

function CommentItem({ comment }: { comment: Comment }) {
  return (
    <div className="flex items-start space-x-3">
      <img
        src={`https://i.pravatar.cc/30?u=${comment.author}`}
        alt={comment.author}
        className="w-8 h-8 rounded-full mt-1"
      />
      <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 flex-1">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span className="font-bold text-gray-900">{comment.author}</span>
          <span>{new Date(comment.time * 1000).toLocaleDateString()}</span>
        </div>
        <p className="text-sm text-gray-800" dangerouslySetInnerHTML={{ __html: comment.text }} />
        {comment.replies && comment.replies.length > 0 && (
          <div className="mt-2 pl-4 border-l-2 border-gray-200 space-y-2">
            {comment.replies.map((reply) => (
              <CommentItem key={reply.id} comment={reply} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
