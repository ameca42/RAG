import type {
  FeedResponse,
  ArticleDetailResponse,
  ChatResponse,
  TopicsResponse,
  SearchResponse
} from '../types/index';

const API_BASE = '/api';

// Fetch articles for feed
export async function fetchFeed(
  page: number = 1,
  perPage: number = 20,
  topic?: string
): Promise<FeedResponse> {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  if (topic) params.append('topic', topic);

  const response = await fetch(`${API_BASE}/articles/feed?${params}`);
  if (!response.ok) throw new Error('Failed to fetch feed');
  return response.json();
}

// Fetch article detail with comments
export async function fetchArticleDetail(itemId: number): Promise<ArticleDetailResponse> {
  const response = await fetch(`${API_BASE}/articles/${itemId}`);
  if (!response.ok) throw new Error('Failed to fetch article');
  return response.json();
}

// Chat with AI about an article
export async function chatWithArticle(
  itemId: number,
  message: string,
  history: { role: string; content: string }[] = []
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/articles/${itemId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) throw new Error('Failed to get AI response');
  return response.json();
}

// Fetch all topics
export async function fetchTopics(): Promise<TopicsResponse> {
  const response = await fetch(`${API_BASE}/topics`);
  if (!response.ok) throw new Error('Failed to fetch topics');
  return response.json();
}

// Search articles
export async function searchArticles(query: string, limit: number = 20): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const response = await fetch(`${API_BASE}/search?${params}`);
  if (!response.ok) throw new Error('Failed to search');
  return response.json();
}
