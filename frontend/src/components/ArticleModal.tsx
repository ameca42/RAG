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