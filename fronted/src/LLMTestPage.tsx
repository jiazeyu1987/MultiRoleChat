import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

interface LLMMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isThinking?: boolean;
}

interface LLMTestPageProps {
  theme: string;
}

const LLMTestPage: React.FC<LLMTestPageProps> = ({ theme }) => {
  const [messages, setMessages] = useState<LLMMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 主题色配置
  const themeColors = {
    blue: 'from-blue-500 to-blue-600',
    purple: 'from-purple-500 to-purple-600',
    green: 'from-green-500 to-green-600',
    red: 'from-red-500 to-red-600',
    orange: 'from-orange-500 to-orange-600',
  };

  const currentColor = themeColors[theme as keyof typeof themeColors] || themeColors.blue;

  // 自动滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 发送消息到LLM
  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: LLMMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    // 添加思考中的消息
    const thinkingMessage: LLMMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
      isThinking: true,
    };
    setMessages(prev => [...prev, thinkingMessage]);

    try {
      // 调用后端LLM API
      const response = await fetch('/api/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          history: messages.filter(m => !m.isThinking).slice(-5) // 只发送最近5条历史消息
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // 添加调试信息
      console.log('LLM API响应数据:', data);
      console.log('响应数据结构:', JSON.stringify(data, null, 2));

      // 验证响应格式
      if (!data || typeof data !== 'object') {
        throw new Error('无效的响应格式');
      }

      // 提取回复内容 - 支持多种可能的格式
      const responseContent = data.data?.response || data.data?.content || data.response || data.content;

      if (!responseContent) {
        console.error('LLM API响应内容为空:', data);
        throw new Error('LLM服务返回了空响应');
      }

      console.log('提取到的回复内容:', responseContent);

      // 移除思考中的消息，添加真实的回复
      setMessages(prev => {
        const filtered = prev.filter(m => !m.isThinking);
        return [...filtered, {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: responseContent,
          timestamp: new Date().toLocaleTimeString(),
        }];
      });

    } catch (err) {
      console.error('LLM API调用失败:', err);
      setError(err instanceof Error ? err.message : '发送消息失败');

      // 移除思考中的消息，添加错误消息
      setMessages(prev => {
        const filtered = prev.filter(m => !m.isThinking);
        return [...filtered, {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: '抱歉，我暂时无法回复您的消息。请检查网络连接或稍后再试。',
          timestamp: new Date().toLocaleTimeString(),
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 处理键盘事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 清除对话历史
  const clearHistory = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">LLM 对话测试</h1>
          <p className="text-gray-600 mt-1">与AI助手进行直接对话测试</p>
        </div>
        <button
          onClick={clearHistory}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          清除历史
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 text-sm">{error}</span>
        </div>
      )}

      {/* 对话区域 */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="h-96 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <Bot className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">开始与AI助手对话吧！</p>
              <p className="text-gray-400 text-sm mt-1">在下方输入框中输入您的问题</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className={`w-8 h-8 rounded-full bg-gradient-to-r ${currentColor} flex items-center justify-center flex-shrink-0`}>
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div
                  className={`max-w-xs lg:max-w-2xl px-4 py-2 rounded-2xl ${
                    message.role === 'user'
                      ? 'bg-gray-100 text-gray-900'
                      : 'bg-gray-50 text-gray-900 border border-gray-200'
                  }`}
                >
                  {message.isThinking ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-gray-500 text-sm">AI 正在思考...</span>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  )}
                  <div className="text-xs text-gray-500 mt-1">
                    {message.timestamp}
                  </div>
                </div>

                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-gray-600" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入区域 */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex gap-3">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题... (按 Enter 发送，Shift+Enter 换行)"
            disabled={isLoading}
            className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
            rows={2}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !inputValue.trim()}
            className={`px-6 py-2 rounded-lg text-white font-medium transition-all ${
              isLoading || !inputValue.trim()
                ? 'bg-gray-300 cursor-not-allowed'
                : `bg-gradient-to-r ${currentColor} hover:shadow-lg transform hover:scale-105`
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* 使用提示 */}
        <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <CheckCircle className="w-3 h-3" />
          <span>支持直接与后端Anthropic LLM服务对话</span>
        </div>
      </div>

      {/* 状态信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-blue-900 mb-2">连接状态</h3>
        <div className="space-y-1 text-sm text-blue-700">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>前端服务: 运行中 (端口 3000)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>后端服务: 运行中 (端口 5000)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            <span>LLM服务: 需要配置Anthropic API密钥</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LLMTestPage;