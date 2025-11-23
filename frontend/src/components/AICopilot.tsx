import { useState } from 'react';
import type { ChatMessage } from '../types/index';

interface AICopilotProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  onClose: () => void;
  loading: boolean;
}

export function AICopilot({ messages, onSend, onClose, loading }: AICopilotProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput('');
  };

  const quickMessages = [
    { label: '📝 总结文章', text: '请用3个要点总结这篇文章' },
    { label: '💬 评论争议', text: '评论区的主要争议点是什么？' },
    { label: '🎯 关键见解', text: '提取评论中最有价值的技术见解' },
  ];

  return (
    <div className="absolute inset-0 bg-white z-20 flex flex-col border-l border-gray-200 shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.1)]">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gradient-to-r from-purple-50 to-pink-50">
        <div className="flex items-center space-x-2 text-purple-700 font-bold">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
            <path fillRule="evenodd" d="M9 4.5a.75.75 0 01.721.544l.813 2.846a3.75 3.75 0 002.576 2.576l2.846.813a.75.75 0 010 1.442l-2.846.813a3.75 3.75 0 00-2.576 2.576l-.813 2.846a.75.75 0 01-1.442 0l-.813-2.846a3.75 3.75 0 00-2.576-2.576l-2.846-.813a.75.75 0 010-1.442l2.846-.813a3.75 3.75 0 002.576-2.576l.813-2.846A.75.75 0 019 4.5z" clipRule="evenodd" />
          </svg>
          <span>AI Copilot</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="flex items-start space-x-2">
            <div className="bg-purple-100 p-2 rounded-lg">🤖</div>
            <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 text-sm">
              我已经阅读了文章和评论。有什么想了解的？
              <div className="mt-3 flex flex-wrap gap-2">
                {quickMessages.map((qm) => (
                  <button
                    key={qm.label}
                    onClick={() => onSend(qm.text)}
                    className="bg-purple-50 text-purple-700 text-xs px-3 py-1.5 rounded-full border border-purple-200 hover:bg-purple-100 transition"
                  >
                    {qm.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex items-start space-x-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && <div className="bg-purple-100 p-2 rounded-lg">🤖</div>}
            <div
              className={`p-3 rounded-2xl shadow-sm text-sm max-w-[80%] ${
                msg.role === 'user'
                  ? 'bg-purple-600 text-white rounded-tr-none'
                  : 'bg-white border border-gray-100 rounded-tl-none'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2">
            <div className="bg-purple-100 p-2 rounded-lg">🤖</div>
            <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 text-sm">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-100 bg-white">
        <form onSubmit={handleSubmit} className="flex items-center space-x-2 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="询问关于文章或评论..."
            className="w-full pl-4 pr-12 py-3 bg-gray-100 border-transparent rounded-full focus:bg-white focus:border-purple-300 focus:ring-0 text-sm transition-all"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="absolute right-2 bg-purple-600 text-white p-2 rounded-full hover:bg-purple-700 transition disabled:opacity-50"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
