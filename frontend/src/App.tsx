import { useState, useEffect, useMemo } from 'react';
import { Menu, Search, Heart, Plus } from 'lucide-react';
import ArticleModal from './components/ArticleModal';
import { generateCover, getRandomAspect } from './utils/coverGenerator';

const API_BASE = 'http://localhost:8000';

const TOPICS = [
  { name: '', label: '推荐' }, { name: 'AI/ML', label: 'AI/机器学习' },
  { name: 'Startups/Business', label: '创业' }, { name: 'Web Development', label: '前端' },
  { name: 'Security/Privacy', label: '安全' }, { name: 'Databases', label: '数据库' }
];

function App() {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTopic, setActiveTopic] = useState('');
  const [page, setPage] = useState(1);
  const [selectedArticle, setSelectedArticle] = useState<any>(null);

  // 响应式列数状态
  const [columnCount, setColumnCount] = useState(2);

  // 监听窗口大小改变列数
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1280) setColumnCount(4);
      else if (window.innerWidth >= 768) setColumnCount(3);
      else setColumnCount(2);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 获取文章
  const fetchArticles = async (reset = false) => {
    if (loading) return;
    setLoading(true);
    const currentPage = reset ? 1 : page;

    try {
      let url = `${API_BASE}/api/articles/feed?page=${currentPage}&per_page=20`;
      if (activeTopic) url += `&topic=${encodeURIComponent(activeTopic)}`;

      const res = await fetch(url);
      const data = await res.json();

      if (data.articles) {
        // 预处理数据：生成封面和比例
        const newItems = data.articles.map((item: any) => {
          const aspect = getRandomAspect();
          const coverUrl = generateCover(item.title, item.topic, item.item_id, aspect.w, aspect.h);
          return {
            ...item,
            aspectClass: aspect.class,
            generatedCover: coverUrl
          };
        });

        if (reset) {
            setArticles(newItems);
            setPage(2);
        } else {
            setArticles(prev => [...prev, ...newItems]);
            setPage(prev => prev + 1);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchArticles(true);
  }, [activeTopic]);

  // 计算瀑布流列数据
  const waterfallColumns = useMemo(() => {
    const cols: any[][] = Array.from({ length: columnCount }, () => []);
    articles.forEach((item, index) => {
        cols[index % columnCount].push(item);
    });
    return cols;
  }, [articles, columnCount]);


  return (
    <div className="relative min-h-screen pb-16 md:pb-0 bg-[#f9f9f9] text-gray-900 font-sans">

      {/* 1. Navbar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md px-4 py-3 flex justify-between items-center shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="flex items-center space-x-4">
            <Menu className="w-6 h-6 text-gray-600" />
            <div className="bg-xhs-red text-white text-xs font-bold px-2 py-1 rounded select-none">HN</div>
        </div>
        <div className="flex space-x-6 text-base font-medium text-gray-500 select-none">
            <button className="text-black font-bold text-lg scale-105 transition-transform">发现</button>
            <button className="hover:text-gray-900 transition-colors">关注</button>
            <button className="hover:text-gray-900 transition-colors">附近</button>
        </div>
        <Search className="w-6 h-6 text-gray-600" />
      </header>

      {/* 2. Topics */}
      <div className="bg-white px-2 py-3 sticky top-[60px] z-30 overflow-x-auto no-scrollbar flex space-x-2 border-b border-gray-100/50">
        {TOPICS.map(topic => (
            <button
                key={topic.name}
                onClick={() => setActiveTopic(topic.name)}
                className={`whitespace-nowrap px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                    activeTopic === topic.name
                    ? 'bg-gray-900 text-white font-bold shadow-md'
                    : 'bg-white border border-gray-100 text-gray-600 hover:bg-gray-50'
                }`}
            >
                {topic.label}
            </button>
        ))}
      </div>

      {/* 3. Masonry Feed */}
      <main className="max-w-7xl mx-auto px-2 py-4 min-h-screen">
         {loading && articles.length === 0 && (
             <div className="flex justify-center py-20">
                 <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-xhs-red"></div>
             </div>
         )}

         <div className="flex items-start gap-2 md:gap-4">
             {waterfallColumns.map((col, colIndex) => (
                 <div key={colIndex} className="flex-1 flex flex-col gap-2 md:gap-4">
                     {col.map((item) => (
                         <div
                            key={item.item_id}
                            onClick={() => setSelectedArticle(item)}
                            className="bg-white rounded-xl overflow-hidden cursor-pointer group hover:shadow-lg transition-all duration-300 animate-in fade-in zoom-in-95"
                         >
                            <div className={`relative w-full overflow-hidden bg-gray-100 ${item.aspectClass}`}>
                                <img src={item.generatedCover} alt={item.title} className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
                            </div>

                            <div className="p-3">
                                <h2 className="font-bold text-sm leading-snug mb-2 text-gray-800 line-clamp-2 tracking-tight">{item.title}</h2>
                                <div className="flex items-center justify-between mt-2">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                        <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${item.author}`} className="w-4 h-4 rounded-full bg-gray-100 shrink-0" />
                                        <span className="text-[11px] text-gray-500 truncate">{item.author}</span>
                                    </div>
                                    <div className="flex items-center gap-1 text-gray-400 group-hover:text-xhs-red transition-colors">
                                        <Heart className="w-3.5 h-3.5" />
                                        <span className="text-xs font-medium">{item.score}</span>
                                    </div>
                                </div>
                            </div>
                         </div>
                     ))}
                 </div>
             ))}
         </div>

         <div className="text-center py-12">
            <button onClick={() => fetchArticles(false)} className="text-gray-400 text-sm hover:text-xhs-red transition-colors">
                {loading ? '加载中...' : '加载更多笔记'}
            </button>
         </div>
      </main>

      {/* 4. Modal */}
      {selectedArticle && (
        <ArticleModal article={selectedArticle} onClose={() => setSelectedArticle(null)} />
      )}

      {/* 5. Mobile Nav */}
      <nav className="md:hidden fixed bottom-0 w-full bg-white border-t border-gray-200 flex justify-around py-3 z-30 pb-safe text-[10px]">
         <a className="flex flex-col items-center text-black font-bold"><span>首页</span></a>
         <a className="flex flex-col items-center text-gray-400"><span>视频</span></a>
         <a className="flex flex-col items-center">
             <div className="bg-xhs-red text-white p-2 rounded-xl shadow-lg shadow-red-200">
                <Plus className="w-5 h-5" />
             </div>
         </a>
         <a className="flex flex-col items-center text-gray-400"><span>消息</span></a>
         <a className="flex flex-col items-center text-gray-400"><span>我</span></a>
      </nav>

    </div>
  );
}

export default App;