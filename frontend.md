这是一个完整的、工程化的 React 版本。

为了达到和之前 Vue 版本完全一致的视觉效果（小红书风格瀑布流、Canvas 动态封面、RAG 对话），我使用了以下技术栈：
*   **React 18+** (Hooks, Functional Components)
*   **Tailwind CSS** (样式)
*   **Lucide React** (图标)
*   **React Markdown** (渲染 Markdown)

### 项目结构
由于代码较长，我将其拆分为几个逻辑文件。如果你使用 Vite 创建项目，结构如下：

1.  `src/utils/coverGenerator.ts` (Canvas 封面生成工具)
2.  `src/components/ArticleModal.tsx` (详情页弹窗：含文章渲染 + 聊天室)
3.  `src/App.tsx` (主入口：瀑布流逻辑 + 状态管理)

---

### 1. 准备工作

首先，创建一个 React + TypeScript + Tailwind 的项目（如果你没有的话）：

```bash
npm create vite@latest hn-xhs-react -- --template react-ts
cd hn-xhs-react
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react react-markdown
```

确保 `tailwind.config.js` 配置了颜色：
```javascript
// tailwind.config.js
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        xhs: {
          red: '#ff2442',
          gray: '#f5f5f5',
          dark: '#333333'
        }
      }
    },
  },
  plugins: [],
}
```

---

### 2. 核心代码实现

#### 文件一：`src/utils/coverGenerator.ts`
这是用于在前端生成“大字报”封面的工具函数。

```typescript
// src/utils/coverGenerator.ts

export const generateCover = (title: string, topic: string, itemId: number, width: number, height: number): string => {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  if (!ctx) return '';

  // 1. 确定性随机配色 (根据 itemId)
  const seed = parseInt(String(itemId).slice(-1)) || 0;
  const gradients = [
      ['#FF9A9E', '#FECFEF'], ['#a18cd1', '#fbc2eb'], ['#84fab0', '#8fd3f4'],
      ['#fccb90', '#d57eeb'], ['#e0c3fc', '#8ec5fc'], ['#fa709a', '#fee140'],
      ['#4facfe', '#00f2fe'], ['#43e97b', '#38f9d7'], ['#30cfd0', '#330867'],
      ['#c471f5', '#fa71cd']
  ];
  const [color1, color2] = gradients[seed % gradients.length];

  // 2. 渐变背景
  const grd = ctx.createLinearGradient(0, 0, width, height);
  grd.addColorStop(0, color1);
  grd.addColorStop(1, color2);
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, width, height);

  // 3. 噪点纹理
  ctx.fillStyle = 'rgba(255,255,255,0.1)';
  for(let i=0; i<100; i++) {
      ctx.beginPath();
      ctx.arc(Math.random()*width, Math.random()*height, Math.random()*2, 0, Math.PI*2);
      ctx.fill();
  }

  // 4. 文字排版
  ctx.fillStyle = '#FFFFFF';
  ctx.shadowColor = 'rgba(0,0,0,0.1)';
  ctx.shadowBlur = 10;
  ctx.shadowOffsetY = 2;
  
  const fontSize = Math.floor(width / 9); 
  ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`;
  ctx.textBaseline = 'middle';

  const words = title.split(' ');
  let line = '';
  let lines = [];
  const maxWidth = width - 60;

  for(let n = 0; n < words.length; n++) {
      const testLine = line + words[n] + ' ';
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && n > 0) {
          lines.push(line);
          line = words[n] + ' ';
      } else {
          line = testLine;
      }
  }
  lines.push(line);
  if (lines.length > 4) lines = lines.slice(0, 4);

  const lineHeight = fontSize * 1.3;
  const totalHeight = lines.length * lineHeight;
  const startY = (height - totalHeight) / 2;

  lines.forEach((l, i) => {
      ctx.fillText(l.trim(), 30, startY + (i * lineHeight));
  });

  // 5. 话题标签
  if (topic) {
      const tagText = `# ${topic}`;
      ctx.font = `bold ${Math.floor(width/20)}px sans-serif`;
      const tagWidth = ctx.measureText(tagText).width + 20;
      
      ctx.fillStyle = 'rgba(0,0,0,0.2)';
      // roundRect is not supported in all typescript defs yet, fallback or polyfill usually needed, 
      // but standard browsers support it. Using rect for simplicity if strict type fails.
      if (ctx.roundRect) {
        ctx.beginPath();
        ctx.roundRect(30, startY - 40, tagWidth, 24, 12);
        ctx.fill();
      } else {
        ctx.fillRect(30, startY - 40, tagWidth, 24);
      }
      
      ctx.fillStyle = '#fff';
      ctx.fillText(tagText, 40, startY - 28);
  }

  // 6. 底部水印
  ctx.font = `${Math.floor(width/24)}px sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.8)';
  ctx.fillText('Hacker News', 30, height - 30);

  return canvas.toDataURL('image/jpeg', 0.8);
};

export const getRandomAspect = () => {
    const r = Math.random();
    if (r > 0.65) return { class: 'aspect-[3/4]', w: 600, h: 800 }; // 长图
    if (r > 0.35) return { class: 'aspect-square', w: 600, h: 600 }; // 方图
    return { class: 'aspect-[4/3]', w: 800, h: 600 }; // 短图
};
```

#### 文件二：`src/components/ArticleModal.tsx`
这是详情页组件，包含 Markdown 渲染和聊天逻辑。

```tsx
// src/components/ArticleModal.tsx
import React, { useState, useEffect, useRef } from 'react';
import { ChevronLeft, Sparkles, Bot, User, Send, Heart, MessageCircle, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Comment {
  id: number;
  author: string;
  time: number;
  text: string;
}

interface ArticleDetail {
  item_id: number;
  title: string;
  url: string;
  author: string;
  timestamp: number;
  content_summary: string;
  comments: Comment[];
  generatedCover?: string;
  [key: string]: any;
}

interface Props {
  article: ArticleDetail; // 传入的基础信息
  onClose: () => void;
}

const API_BASE = 'http://localhost:8000';

const ArticleModal: React.FC<Props> = ({ article: initialArticle, onClose }) => {
  const [detail, setDetail] = useState<ArticleDetail>(initialArticle);
  const [activeTab, setActiveTab] = useState<'comments' | 'chat'>('comments');
  const [analysis, setAnalysis] = useState<any>(null);
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string, loading?: boolean}>>([]);
  const [inputMsg, setInputMsg] = useState('');
  const scrollBoxRef = useRef<HTMLDivElement>(null);

  // 初始化：获取详情 + AI 分析
  useEffect(() => {
    document.body.style.overflow = 'hidden';

    // Fetch full details
    fetch(`${API_BASE}/api/articles/${initialArticle.item_id}`)
      .then(r => r.json())
      .then(data => {
        setDetail(prev => ({ ...prev, ...data.article, comments: data.comments }));
      })
      .catch(console.error);

    // Fetch AI Analysis
    fetch(`${API_BASE}/api/chat/analyze-article`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: String(initialArticle.item_id) })
    })
    .then(r => r.json())
    .then(data => setAnalysis(data))
    .catch(console.error);

    return () => { document.body.style.overflow = ''; };
  }, [initialArticle.item_id]);

  // 滚动到底部
  useEffect(() => {
    if (activeTab === 'chat' && scrollBoxRef.current) {
      scrollBoxRef.current.scrollTop = scrollBoxRef.current.scrollHeight;
    }
  }, [chatHistory, activeTab]);

  const handleSend = async () => {
    if (!inputMsg.trim()) return;

    if (activeTab === 'chat') {
      const msg = inputMsg;
      setInputMsg('');
      setChatHistory(prev => [...prev, { role: 'user', content: msg }]);
      setChatHistory(prev => [...prev, { role: 'ai', content: '', loading: true }]);

      try {
        const res = await fetch(`${API_BASE}/api/articles/${detail.item_id}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: msg,
            history: chatHistory.filter(m => !m.loading).map(m => ({ role: m.role, content: m.content }))
          })
        });
        const data = await res.json();
        setChatHistory(prev => {
          const newHistory = [...prev];
          newHistory.pop(); // remove loading
          newHistory.push({ role: 'ai', content: data.response });
          return newHistory;
        });
      } catch (e) {
        setChatHistory(prev => {
            const newHistory = [...prev];
            newHistory.pop(); 
            newHistory.push({ role: 'ai', content: '网络错误，请重试' });
            return newHistory;
        });
      }
    } else {
      // 本地模拟评论
      const newComment = {
          id: Date.now(),
          author: 'Me',
          time: Date.now() / 1000,
          text: inputMsg
      };
      setDetail(prev => ({
          ...prev,
          comments: [newComment, ...(prev.comments || [])]
      }));
      setInputMsg('');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm md:p-8 animate-in fade-in duration-200" onClick={onClose}>
      <div 
        className="bg-white w-full h-full md:h-[90vh] md:w-[1100px] md:rounded-2xl shadow-2xl flex flex-col md:flex-row overflow-hidden relative"
        onClick={e => e.stopPropagation()}
      >
        {/* Mobile Close */}
        <button onClick={onClose} className="absolute top-4 left-4 z-50 bg-white/90 p-2 rounded-full md:hidden shadow-lg">
          <ChevronLeft className="w-6 h-6 text-gray-800" />
        </button>

        {/* LEFT: Content */}
        <div className="w-full md:w-3/5 h-full overflow-y-auto no-scrollbar bg-white">
          <div className="relative w-full aspect-video bg-gray-100">
             {detail.generatedCover && <img src={detail.generatedCover} className="absolute inset-0 w-full h-full object-cover" />}
          </div>
          
          <div className="p-6 pb-20 md:pb-10 max-w-3xl mx-auto">
            <h1 className="text-2xl font-bold mb-4 text-gray-900 leading-tight">{detail.title}</h1>
            <div className="flex items-center justify-between text-xs text-gray-400 mb-6 pb-4 border-b border-gray-100">
                <span>{new Date(detail.timestamp * 1000).toLocaleDateString()}</span>
                <a href={detail.url} target="_blank" rel="noreferrer" className="flex items-center text-blue-600 hover:underline">
                    查看原文 <ExternalLink className="w-3 h-3 ml-1" />
                </a>
            </div>
            
            <div className="markdown-body prose prose-sm max-w-none text-justify text-gray-800">
              <ReactMarkdown>{detail.content_summary || ''}</ReactMarkdown>
            </div>
          </div>
        </div>

        {/* RIGHT: Interaction */}
        <div className="w-full md:w-2/5 h-full bg-gray-50 flex flex-col border-l border-gray-100 relative">
          
          {/* Author Header */}
          <div className="p-4 bg-white border-b border-gray-100 flex justify-between items-center shrink-0">
            <div className="flex items-center gap-3">
              <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${detail.author}`} className="w-9 h-9 rounded-full border bg-gray-50" />
              <div>
                  <div className="text-sm font-bold text-gray-900">{detail.author}</div>
                  <div className="text-[10px] text-gray-400">知名博主</div>
              </div>
            </div>
            <button className="border border-xhs-red text-xhs-red px-5 py-1.5 rounded-full text-xs font-bold hover:bg-red-50 transition">关注</button>
          </div>

          {/* Tabs */}
          <div className="bg-white flex border-b border-gray-100 shrink-0">
             <button 
                onClick={() => setActiveTab('comments')} 
                className={`flex-1 py-3 text-sm font-medium relative transition-colors ${activeTab === 'comments' ? 'font-bold text-gray-900' : 'text-gray-400'}`}
             >
                评论 {detail.comments?.length || 0}
                {activeTab === 'comments' && <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-xhs-red rounded-full" />}
             </button>
             <button 
                onClick={() => setActiveTab('chat')} 
                className={`flex-1 py-3 text-sm font-medium relative transition-colors ${activeTab === 'chat' ? 'font-bold text-gray-900' : 'text-gray-400'}`}
             >
                <span className="flex items-center justify-center gap-1">
                    <Sparkles className={`w-3.5 h-3.5 ${activeTab === 'chat' ? 'text-purple-500' : ''}`} />
                    AI 伴读
                </span>
                {activeTab === 'chat' && <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-purple-500 rounded-full" />}
             </button>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-4 bg-white scroll-smooth" ref={scrollBoxRef}>
            
            {activeTab === 'comments' ? (
                <div className="space-y-6 min-h-full">
                    {!detail.comments?.length && (
                        <div className="text-center py-10 text-gray-400 text-xs">暂无评论，来抢沙发吧</div>
                    )}
                    {detail.comments?.map((c) => (
                        <div key={c.id} className="flex gap-3">
                             <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${c.author}`} className="w-8 h-8 rounded-full shrink-0 border border-gray-100" />
                             <div className="flex-1">
                                <div className="text-xs text-gray-400 mb-1">{c.author}</div>
                                <div className="text-sm text-gray-800 leading-relaxed">
                                    <ReactMarkdown>{c.text}</ReactMarkdown>
                                </div>
                                <div className="flex gap-4 mt-2 text-gray-400">
                                    <Heart className="w-3.5 h-3.5 cursor-pointer hover:text-xhs-red" />
                                    <MessageCircle className="w-3.5 h-3.5 cursor-pointer hover:text-blue-500" />
                                </div>
                             </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="space-y-4 pb-4">
                    <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                        <div className="flex items-center gap-2 mb-2 text-purple-700 font-bold text-sm">
                            <Bot className="w-4 h-4" /> 
                            <span>AI 智能研报</span>
                        </div>
                        {analysis ? (
                             <div className="text-sm text-purple-900 leading-relaxed markdown-body">
                                <ReactMarkdown>{analysis.summary?.key_insights?.[0] || '分析完成'}</ReactMarkdown>
                             </div>
                        ) : (
                             <div className="flex space-x-1 h-5 items-center">
                                <span className="text-xs text-gray-400">正在阅读文章...</span>
                                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce"></div>
                             </div>
                        )}
                    </div>

                    {chatHistory.map((msg, idx) => (
                        <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                             <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'ai' ? 'bg-purple-100 text-purple-600' : 'bg-gray-800 text-white'}`}>
                                {msg.role === 'ai' ? <Sparkles className="w-4 h-4" /> : <User className="w-4 h-4" />}
                             </div>
                             <div className={`max-w-[85%] text-sm p-3 rounded-2xl shadow-sm ${msg.role === 'ai' ? 'bg-white text-gray-800 rounded-tl-none border border-gray-100' : 'bg-xhs-red text-white rounded-tr-none'}`}>
                                {msg.loading ? (
                                     <div className="flex space-x-1 items-center h-5 px-1">
                                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                                     </div>
                                ) : (
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                )}
                             </div>
                        </div>
                    ))}
                </div>
            )}
          </div>

          {/* Input Area */}
          <div className="p-3 bg-white border-t border-gray-100 shrink-0 safe-pb">
            <div className={`flex items-center gap-2 bg-gray-100 rounded-full px-4 py-2 transition-all focus-within:bg-white focus-within:ring-2 ${activeTab === 'chat' ? 'focus-within:ring-purple-100' : 'focus-within:ring-red-100'}`}>
                {activeTab === 'chat' ? <Sparkles className="w-4 h-4 text-purple-500" /> : <Send className="w-4 h-4 text-gray-400" />}
                <input 
                    value={inputMsg}
                    onChange={(e) => setInputMsg(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    type="text" 
                    placeholder={activeTab === 'chat' ? "问 AI 关于文章..." : "说点什么..."}
                    className="bg-transparent flex-1 text-sm outline-none placeholder-gray-400"
                />
                <button 
                    onClick={handleSend}
                    disabled={!inputMsg.trim()}
                    className={`font-bold text-sm px-2 ${activeTab === 'chat' ? 'text-purple-600' : 'text-xhs-red'} disabled:opacity-50`}
                >
                    发送
                </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ArticleModal;
```

#### 文件三：`src/App.tsx`
这是主入口，包含瀑布流逻辑。

```tsx
// src/App.tsx
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
```

---

### 如何运行

1.  将上述文件放入 Vite 项目的对应位置。
2.  确保你的 FastAPI 后端正在 `localhost:8000` 运行。
3.  运行前端：`npm run dev`。
4.  打开浏览器访问 `http://localhost:5173`。

### 视觉一致性保证

这个 React 版本在视觉上做了以下细节对齐：
1.  **Masonry 逻辑**：使用了相同的 Flex Column 算法（`useMemo` 计算），保证了“错落有致”的布局。
2.  **Cover 生成**：`generateCover` 函数被完美移植，保留了 10 种渐变色和文字换行算法。
3.  **样式类名**：完全复用了 Tailwind 的 CSS 类，包括自定义的 `xhs-red` 颜色、圆角大小和阴影效果。
4.  **交互动画**：添加了 React 原生的 `animate-in` 类（Tailwind 插件或自定义 CSS）让卡片出现时有轻微的上浮效果。