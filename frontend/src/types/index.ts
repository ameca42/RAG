// Article types matching backend data structure
export interface Article {
  item_id: number;
  title: string;
  url: string;
  author: string;
  score: number;
  descendants: number;
  timestamp: number;
  crawl_date: string;
  content_type: string;
  content_summary: string | null;
  comments_summary: string | null;
  top_comments: TopComment[];
  topic: string;
  tags: string[];
  classification_confidence: string;
  ai_summary?: string;
}

export interface TopComment {
  id: number;
  author: string;
  text: string;
  score: number;
  time: number;
}

export interface Comment {
  id: number;
  author: string;
  text: string;
  time: number;
  replies?: Comment[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface TopicCount {
  topic: string;
  count: number;
}

// API Response types
export interface FeedResponse {
  articles: Article[];
  total: number;
  page: number;
  per_page: number;
}

export interface ArticleDetailResponse {
  article: Article;
  comments: Comment[];
}

export interface ChatResponse {
  response: string;
  sources?: string[];
}

export interface TopicsResponse {
  topics: TopicCount[];
}

export interface SearchResponse {
  results: Article[];
  total: number;
}
