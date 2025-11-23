import type { Article } from '../types/index';

interface ArticleCardProps {
  article: Article;
  onClick: () => void;
}

// Color mapping for topics
const topicColors: Record<string, string> = {
  'AI/ML': 'purple',
  'Programming Languages': 'blue',
  'Web Development': 'pink',
  'Databases': 'green',
  'Security/Privacy': 'red',
  'Startups/Business': 'orange',
  'Hardware/IoT': 'teal',
  'Science': 'cyan',
  'Open Source': 'emerald',
  'Career/Jobs': 'amber',
};

export function ArticleCard({ article, onClick }: ArticleCardProps) {
  const color = topicColors[article.topic] || 'gray';
  const domain = article.url ? new URL(article.url).hostname.replace('www.', '') : 'hackernews.com';

  // Generate placeholder image based on topic
  const imageUrl = `https://source.unsplash.com/random/400x300?${article.topic.split('/')[0].toLowerCase()}`;

  return (
    <div
      className="masonry-item break-inside-avoid mb-4 group cursor-pointer"
      onClick={onClick}
    >
      <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-gray-100">
        {/* Image */}
        <div className="aspect-w-4 aspect-h-3 bg-gray-100 relative overflow-hidden">
          <img
            src={imageUrl}
            alt={article.title}
            className="object-cover w-full h-48 group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
          <div className={`absolute top-3 left-3 bg-white/90 backdrop-blur px-2 py-1 rounded-md text-xs font-bold text-${color}-600`}>
            #{article.topic}
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          <h2 className="font-bold text-lg leading-tight mb-2 line-clamp-2 group-hover:text-orange-600 transition-colors">
            {article.title}
          </h2>

          {/* AI Summary */}
          {article.ai_summary || article.content_summary ? (
            <p className="text-gray-600 text-sm line-clamp-3 mb-4 bg-gray-50 p-2 rounded-lg">
              🤖 AI摘要: {article.ai_summary || article.content_summary?.slice(0, 150) + '...'}
            </p>
          ) : null}

          {/* Meta info */}
          <div className="flex items-center justify-between text-xs text-gray-400 font-medium">
            <div className="flex items-center space-x-1">
              <span>{domain}</span>
            </div>
            <div className="flex items-center space-x-3">
              <span className="flex items-center">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"/>
                </svg>
                {article.score}
              </span>
              <span className="flex items-center text-orange-500">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd"/>
                </svg>
                {article.descendants || 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
