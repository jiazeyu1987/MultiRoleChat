import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { useInView } from 'react-intersection-observer';
import {
  Send,
  MessageSquare,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Copy,
  ChevronDown,
  ChevronRight,
  Zap,
  Eye,
  EyeOff,
  RefreshCw,
  Download
} from 'lucide-react';

interface LLMInteraction {
  id: number;
  session_id: number;
  step_id?: number;
  session_role_id?: number;
  provider: string;
  model?: string;
  request_id?: string;
  system_prompt?: string;
  user_prompt: string;
  full_prompt?: any;
  response_content?: string;
  raw_response?: any;
  status: 'pending' | 'streaming' | 'completed' | 'failed' | 'timeout';
  error_message?: string;
  latency_ms?: number;
  duration_seconds?: number;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  step_info?: {
    id: number;
    name: string;
    type: string;
  };
  role_info?: {
    id: number;
    name: string;
    role_ref: string;
  };
}

interface LLMIODisplayProps {
  sessionId: number;
  compact?: boolean;
  showDetails?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  maxItems?: number;
  showStreaming?: boolean;
  showDebugInfo?: boolean;
  enableVirtualScrolling?: boolean;
  virtualScrollThreshold?: number;
  virtualItemHeight?: number;
}

interface LLMInteractionData {
  interactions: LLMInteraction[];
  pagination: any;
  statistics: {
    total_interactions: number;
    completed_interactions: number;
    failed_interactions: number;
    active_interactions: number;
    success_rate: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    average_latency_ms: number;
  };
}

const LLMIODisplay: React.FC<LLMIODisplayProps> = ({
  sessionId,
  compact = false,
  showDetails = true,
  autoRefresh = true,
  refreshInterval = 3000,
  maxItems = 50,
  showStreaming = true,
  showDebugInfo = false,
  enableVirtualScrolling = true,
  virtualScrollThreshold = 100,
  virtualItemHeight = 200
}) => {
  const [interactionData, setInteractionData] = useState<LLMInteractionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedInteractions, setExpandedInteractions] = useState<Set<number>>(new Set());
  const [showFullPrompt, setShowFullPrompt] = useState<Set<number>>(new Set());
  const [showFullResponse, setShowFullResponse] = useState<Set<number>>(new Set());
  const [activeStreaming, setActiveStreaming] = useState<Map<number, string>>(new Map());
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [filter, setFilter] = useState<string>('all'); // all, completed, failed, active

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'streaming':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'timeout':
        return <XCircle className="w-4 h-4 text-orange-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'streaming':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'timeout':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 格式化时间
  const formatDuration = (latencyMs?: number) => {
    if (!latencyMs) return 'N/A';
    if (latencyMs < 1000) return `${latencyMs}ms`;
    return `${(latencyMs / 1000).toFixed(2)}s`;
  };

  // 格式化令牌数
  const formatTokens = (tokens?: number) => {
    if (!tokens) return '0';
    if (tokens < 1000) return tokens.toString();
    return `${(tokens / 1000).toFixed(1)}K`;
  };

  // 复制到剪贴板
  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // 这里可以添加一个toast通知
      console.log(`${type} copied to clipboard`);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // 切换交互展开状态
  const toggleInteractionExpanded = (interactionId: number) => {
    const newExpanded = new Set(expandedInteractions);
    if (newExpanded.has(interactionId)) {
      newExpanded.delete(interactionId);
    } else {
      newExpanded.add(interactionId);
    }
    setExpandedInteractions(newExpanded);
  };

  // 切换完整提示词显示
  const toggleFullPrompt = (interactionId: number) => {
    const newShow = new Set(showFullPrompt);
    if (newShow.has(interactionId)) {
      newShow.delete(interactionId);
    } else {
      newShow.add(interactionId);
    }
    setShowFullPrompt(newShow);
  };

  // 切换完整响应显示
  const toggleFullResponse = (interactionId: number) => {
    const newShow = new Set(showFullResponse);
    if (newShow.has(interactionId)) {
      newShow.delete(interactionId);
    } else {
      newShow.add(interactionId);
    }
    setShowFullResponse(newShow);
  };

  // 过滤交互记录
  const filteredInteractions = interactionData?.interactions.filter(interaction => {
    switch (filter) {
      case 'completed':
        return interaction.status === 'completed';
      case 'failed':
        return interaction.status === 'failed';
      case 'active':
        return interaction.status === 'pending' || interaction.status === 'streaming';
      default:
        return true;
    }
  }).slice(0, maxItems) || [];

  // 确定是否使用虚拟滚动
  const shouldUseVirtualScrolling = enableVirtualScrolling && filteredInteractions.length > virtualScrollThreshold;

  // 动态调整项目高度（考虑展开状态）
  const getItemHeight = useCallback((index: number) => {
    const interaction = filteredInteractions[index];
    const isExpanded = expandedInteractions.has(interaction.id);

    if (!isExpanded) {
      return 80; // 紧凑模式的高度
    }

    // 基础高度 + 动态内容高度估算
    let height = 200;

    if (interaction.system_prompt) height += 120;
    if (showFullPrompt.has(interaction.id)) height += 100;
    if (interaction.response_content) height += 150;
    if (showFullResponse.has(interaction.id)) height += 100;
    if (activeStreaming.get(interaction.id)) height += 120;
    if (interaction.error_message) height += 80;
    if (showDebugInfo && interaction.raw_response) height += 100;

    return Math.min(height, 800); // 限制最大高度
  }, [expandedInteractions, filteredInteractions, showFullPrompt, showFullResponse, activeStreaming, showDebugInfo]);

  // 创建虚拟行渲染器
  const VirtualInteractionRow = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const interaction = filteredInteractions[index];
    const isExpanded = expandedInteractions.has(interaction.id);
    const streamingContent = activeStreaming.get(interaction.id);
    const showPrompt = showFullPrompt.has(interaction.id);
    const showResponse = showFullResponse.has(interaction.id);

    // 使用 Intersection Observer 来优化性能
    const { ref, inView } = useInView({
      threshold: 0,
      triggerOnce: false,
      rootMargin: '200px'
    });

    return (
      <div style={style} ref={ref}>
        {inView && (
          <div className="border-b border-gray-100 last:border-b-0">
            <div className="px-6 py-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(interaction.status)}
                  <span className="text-sm font-medium text-gray-900">
                    {interaction.provider}
                    {interaction.model && ` (${interaction.model})`}
                  </span>
                  {interaction.role_info && (
                    <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                      {interaction.role_info.name}
                    </span>
                  )}
                  {interaction.step_info && (
                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                      {interaction.step_info.name}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-3">
                  {interaction.usage && (
                    <span className="text-xs text-gray-500">
                      {formatTokens(interaction.usage.total_tokens)} tokens
                    </span>
                  )}
                  {interaction.latency_ms && (
                    <span className="text-xs text-gray-500">
                      {formatDuration(interaction.latency_ms)}
                    </span>
                  )}
                  <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(interaction.status)}`}>
                    {interaction.status}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  {new Date(interaction.created_at).toLocaleString()}
                </span>
                <div className="flex items-center space-x-2">
                  {showDebugInfo && interaction.request_id && (
                    <span className="text-xs text-gray-400">
                      ID: {interaction.request_id}
                    </span>
                  )}
                  <button
                    onClick={() => toggleInteractionExpanded(interaction.id)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* 展开的详细内容 */}
              {isExpanded && showDetails && (
                <div className="mt-3 space-y-3">
                  {/* 用户提示词 */}
                  <div className="border border-gray-200 rounded">
                    <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
                      <div className="flex items-center text-sm font-medium text-gray-700">
                        <Send className="w-4 h-4 mr-2" />
                        User Prompt
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => copyToClipboard(interaction.user_prompt, 'User prompt')}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => toggleFullPrompt(interaction.id)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {showPrompt ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <div className="p-3">
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
                        {showPrompt ? interaction.user_prompt :
                         (interaction.user_prompt.length > 200 ?
                          interaction.user_prompt.substring(0, 200) + '...' :
                          interaction.user_prompt)}
                      </pre>
                    </div>
                  </div>

                  {/* 系统提示词 */}
                  {interaction.system_prompt && (
                    <div className="border border-gray-200 rounded">
                      <div className="flex items-center justify-between px-3 py-2 bg-blue-50 border-b border-gray-200">
                        <div className="flex items-center text-sm font-medium text-gray-700">
                          <AlertCircle className="w-4 h-4 mr-2" />
                          System Prompt
                        </div>
                        <button
                          onClick={() => copyToClipboard(interaction.system_prompt!, 'System prompt')}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="p-3">
                        <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-blue-50 rounded p-2 max-h-32 overflow-y-auto">
                          {interaction.system_prompt}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 流式内容 */}
                  {streamingContent && (
                    <div className="border border-blue-200 rounded bg-blue-50">
                      <div className="flex items-center justify-between px-3 py-2 bg-blue-100 border-b border-blue-200">
                        <div className="flex items-center text-sm font-medium text-blue-700">
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Streaming Response
                        </div>
                      </div>
                      <div className="p-3">
                        <pre className="text-sm text-blue-900 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                          {streamingContent}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 响应内容 */}
                  {interaction.response_content && (
                    <div className="border border-gray-200 rounded">
                      <div className="flex items-center justify-between px-3 py-2 bg-green-50 border-b border-gray-200">
                        <div className="flex items-center text-sm font-medium text-gray-700">
                          <MessageSquare className="w-4 h-4 mr-2" />
                          Response
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => copyToClipboard(interaction.response_content!, 'Response')}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => toggleFullResponse(interaction.id)}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            {showResponse ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>
                      <div className="p-3">
                        <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-green-50 rounded p-2 max-h-32 overflow-y-auto">
                          {showResponse ? interaction.response_content :
                           (interaction.response_content.length > 300 ?
                            interaction.response_content.substring(0, 300) + '...' :
                            interaction.response_content)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 错误信息 */}
                  {interaction.error_message && (
                    <div className="border border-red-200 rounded bg-red-50">
                      <div className="flex items-center px-3 py-2 bg-red-100 border-b border-red-200">
                        <XCircle className="w-4 h-4 mr-2 text-red-600" />
                        <span className="text-sm font-medium text-red-700">Error</span>
                      </div>
                      <div className="p-3">
                        <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                          {interaction.error_message}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 调试信息 */}
                  {showDebugInfo && interaction.raw_response && (
                    <div className="border border-gray-200 rounded">
                      <div className="flex items-center px-3 py-2 bg-gray-100 border-b border-gray-200">
                        <span className="text-sm font-medium text-gray-700">Raw Response</span>
                      </div>
                      <div className="p-3">
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-gray-900 text-green-400 rounded p-2 max-h-32 overflow-y-auto">
                          {JSON.stringify(interaction.raw_response, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }, [filteredInteractions, expandedInteractions, activeStreaming, showFullPrompt, showFullResponse, showDetails, showDebugInfo, getStatusIcon, formatTokens, formatDuration, copyToClipboard, toggleInteractionExpanded, toggleFullPrompt, toggleFullResponse]);

  // 为虚拟列表生成动态高度数组
  const itemSizes = useMemo(() => {
    if (!shouldUseVirtualScrolling) return [];
    return filteredInteractions.map((_, index) => getItemHeight(index));
  }, [shouldUseVirtualScrolling, filteredInteractions, getItemHeight]);

  // 获取交互数据
  const fetchInteractionData = async () => {
    try {
      const statusFilter = filter === 'all' ? undefined : filter;
      const response = await fetch(
        `/api/sessions/${sessionId}/llm-interactions?include_details=true&per_page=${maxItems}${statusFilter ? `&status=${statusFilter}` : ''}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch LLM interactions');
      }

      const result = await response.json();
      if (result.success) {
        setInteractionData(result.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // 设置实时更新
  const setupRealtimeUpdates = () => {
    if (!showStreaming || eventSource) return;

    try {
      const source = new EventSource(`/api/sessions/${sessionId}/live`);

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.event) {
            case 'llm_request_started':
              // 处理请求开始
              break;
            case 'llm_response_streaming':
              // 处理流式响应
              if (data.interaction_id) {
                setActiveStreaming(prev => {
                  const newMap = new Map(prev);
                  const existingContent = newMap.get(data.interaction_id) || '';
                  newMap.set(data.interaction_id, existingContent + (data.content_chunk || ''));
                  return newMap;
                });
              }
              break;
            case 'llm_response_completed':
              // 响应完成，清除流式内容
              if (data.interaction_id) {
                setActiveStreaming(prev => {
                  const newMap = new Map(prev);
                  newMap.delete(data.interaction_id);
                  return newMap;
                });
                // 重新获取数据
                fetchInteractionData();
              }
              break;
            case 'llm_request_failed':
            case 'llm_request_timeout':
              // 请求失败或超时
              if (data.interaction_id) {
                setActiveStreaming(prev => {
                  const newMap = new Map(prev);
                  newMap.delete(data.interaction_id);
                  return newMap;
                });
                // 重新获取数据
                fetchInteractionData();
              }
              break;
          }
        } catch (err) {
          console.error('Error parsing SSE message:', err);
        }
      };

      source.onerror = (err) => {
        console.error('SSE error:', err);
        source.close();
        setEventSource(null);
      };

      setEventSource(source);
    } catch (err) {
      console.error('Failed to setup SSE:', err);
    }
  };

  // 初始加载数据
  useEffect(() => {
    fetchInteractionData();
  }, [sessionId, filter, maxItems]);

  // 设置实时更新
  useEffect(() => {
    if (showStreaming) {
      setupRealtimeUpdates();
    }

    return () => {
      if (eventSource) {
        eventSource.close();
        setEventSource(null);
      }
    };
  }, [sessionId, showStreaming]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchInteractionData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, sessionId, filter, maxItems]);

  // 导出数据
  const exportData = () => {
    if (!interactionData) return;

    const exportData = {
      session_id: sessionId,
      export_time: new Date().toISOString(),
      statistics: interactionData.statistics,
      interactions: filteredInteractions
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm_interactions_session_${sessionId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        <span>Loading LLM interactions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
        <div className="flex items-center">
          <XCircle className="w-5 h-5 text-red-500 mr-2" />
          <span className="text-red-700">Error loading LLM interactions: {error}</span>
        </div>
      </div>
    );
  }

  if (!interactionData) {
    return (
      <div className="p-4 border border-gray-200 bg-gray-50 rounded-lg">
        <span className="text-gray-600">No LLM interaction data available</span>
      </div>
    );
  }

  // 渲染紧凑视图
  if (compact) {
    return (
      <div className="p-4 border border-gray-200 rounded-lg bg-white">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">LLM Interactions</h3>
          <div className="flex items-center space-x-2">
            {showStreaming && (
              <div className="flex items-center text-xs text-blue-600">
                <Zap className="w-3 h-3 mr-1" />
                Live
              </div>
            )}
            <span className="text-xs text-gray-500">
              {interactionData.statistics.active_interactions} active
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-lg font-semibold text-green-600">
              {interactionData.statistics.completed_interactions}
            </div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-blue-600">
              {interactionData.statistics.total_tokens}
            </div>
            <div className="text-xs text-gray-500">Total Tokens</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-red-600">
              {interactionData.statistics.failed_interactions}
            </div>
            <div className="text-xs text-gray-500">Failed</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* 头部信息 */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">LLM I/O Display</h2>
            <p className="text-sm text-gray-600">
              Session {sessionId} • {filteredInteractions.length} interactions
            </p>
          </div>
          <div className="flex items-center space-x-3">
            {/* 实时状态指示器 */}
            {showStreaming && (
              <div className="flex items-center text-sm text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
                Live
              </div>
            )}

            {/* 导出按钮 */}
            <button
              onClick={exportData}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 flex items-center"
            >
              <Download className="w-3 h-3 mr-1" />
              Export
            </button>
          </div>
        </div>

        {/* 过滤器 */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            {['all', 'active', 'completed', 'failed'].map((filterOption) => (
              <button
                key={filterOption}
                onClick={() => setFilter(filterOption)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  filter === filterOption
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                } border`}
              >
                {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* 统计信息 */}
        <div className="mt-4 grid grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-600">
              {interactionData.statistics.total_interactions}
            </div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">
              {formatTokens(interactionData.statistics.total_tokens)}
            </div>
            <div className="text-xs text-gray-500">Tokens</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-purple-600">
              {formatDuration(interactionData.statistics.average_latency_ms)}
            </div>
            <div className="text-xs text-gray-500">Avg Latency</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">
              {interactionData.statistics.success_rate.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Success Rate</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-indigo-600">
              {shouldUseVirtualScrolling ? '✓' : '○'}
            </div>
            <div className="text-xs text-gray-500">Virtual Scroll</div>
          </div>
        </div>
      </div>

      {/* 交互列表 */}
      <div className="max-h-96">
        {filteredInteractions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No LLM interactions found
          </div>
        ) : shouldUseVirtualScrolling ? (
          <div className="h-96">
            <List
              height={384} // 96 * 4 (h-96 = 24rem = 384px)
              itemCount={filteredInteractions.length}
              itemSize={getItemHeight}
              itemData={filteredInteractions}
              overscanCount={5}
            >
              {VirtualInteractionRow}
            </List>
          </div>
        ) : (
          <div className="overflow-y-auto h-96">
            {filteredInteractions.map((interaction) => {
              const isExpanded = expandedInteractions.has(interaction.id);
              const streamingContent = activeStreaming.get(interaction.id);
              const showPrompt = showFullPrompt.has(interaction.id);
              const showResponse = showFullResponse.has(interaction.id);

              return (
                <div key={interaction.id} className="border-b border-gray-100 last:border-b-0">
                  <div className="px-6 py-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(interaction.status)}
                        <span className="text-sm font-medium text-gray-900">
                          {interaction.provider}
                          {interaction.model && ` (${interaction.model})`}
                        </span>
                        {interaction.role_info && (
                          <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                            {interaction.role_info.name}
                          </span>
                        )}
                        {interaction.step_info && (
                          <span className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                            {interaction.step_info.name}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-3">
                        {interaction.usage && (
                          <span className="text-xs text-gray-500">
                            {formatTokens(interaction.usage.total_tokens)} tokens
                          </span>
                        )}
                        {interaction.latency_ms && (
                          <span className="text-xs text-gray-500">
                            {formatDuration(interaction.latency_ms)}
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(interaction.status)}`}>
                          {interaction.status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        {new Date(interaction.created_at).toLocaleString()}
                      </span>
                      <div className="flex items-center space-x-2">
                        {showDebugInfo && interaction.request_id && (
                          <span className="text-xs text-gray-400">
                            ID: {interaction.request_id}
                          </span>
                        )}
                        <button
                          onClick={() => toggleInteractionExpanded(interaction.id)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* 展开的详细内容 */}
                    {isExpanded && showDetails && (
                      <div className="mt-3 space-y-3">
                        {/* 用户提示词 */}
                        <div className="border border-gray-200 rounded">
                          <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
                            <div className="flex items-center text-sm font-medium text-gray-700">
                              <Send className="w-4 h-4 mr-2" />
                              User Prompt
                            </div>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => copyToClipboard(interaction.user_prompt, 'User prompt')}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                <Copy className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => toggleFullPrompt(interaction.id)}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {showPrompt ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                              </button>
                            </div>
                          </div>
                          <div className="p-3">
                            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
                              {showPrompt ? interaction.user_prompt :
                               (interaction.user_prompt.length > 200 ?
                                interaction.user_prompt.substring(0, 200) + '...' :
                                interaction.user_prompt)}
                            </pre>
                          </div>
                        </div>

                        {/* 系统提示词 */}
                        {interaction.system_prompt && (
                          <div className="border border-gray-200 rounded">
                            <div className="flex items-center justify-between px-3 py-2 bg-blue-50 border-b border-gray-200">
                              <div className="flex items-center text-sm font-medium text-gray-700">
                                <AlertCircle className="w-4 h-4 mr-2" />
                                System Prompt
                              </div>
                              <button
                                onClick={() => copyToClipboard(interaction.system_prompt!, 'System prompt')}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                <Copy className="w-4 h-4" />
                              </button>
                            </div>
                            <div className="p-3">
                              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-blue-50 rounded p-2 max-h-32 overflow-y-auto">
                                {interaction.system_prompt}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* 流式内容 */}
                        {streamingContent && (
                          <div className="border border-blue-200 rounded bg-blue-50">
                            <div className="flex items-center justify-between px-3 py-2 bg-blue-100 border-b border-blue-200">
                              <div className="flex items-center text-sm font-medium text-blue-700">
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Streaming Response
                              </div>
                            </div>
                            <div className="p-3">
                              <pre className="text-sm text-blue-900 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
                                {streamingContent}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* 响应内容 */}
                        {interaction.response_content && (
                          <div className="border border-gray-200 rounded">
                            <div className="flex items-center justify-between px-3 py-2 bg-green-50 border-b border-gray-200">
                              <div className="flex items-center text-sm font-medium text-gray-700">
                                <MessageSquare className="w-4 h-4 mr-2" />
                                Response
                              </div>
                              <div className="flex items-center space-x-2">
                                <button
                                  onClick={() => copyToClipboard(interaction.response_content!, 'Response')}
                                  className="text-gray-400 hover:text-gray-600"
                                >
                                  <Copy className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => toggleFullResponse(interaction.id)}
                                  className="text-gray-400 hover:text-gray-600"
                                >
                                  {showResponse ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                              </div>
                            </div>
                            <div className="p-3">
                              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-green-50 rounded p-2 max-h-32 overflow-y-auto">
                                {showResponse ? interaction.response_content :
                                 (interaction.response_content.length > 300 ?
                                  interaction.response_content.substring(0, 300) + '...' :
                                  interaction.response_content)}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* 错误信息 */}
                        {interaction.error_message && (
                          <div className="border border-red-200 rounded bg-red-50">
                            <div className="flex items-center px-3 py-2 bg-red-100 border-b border-red-200">
                              <XCircle className="w-4 h-4 mr-2 text-red-600" />
                              <span className="text-sm font-medium text-red-700">Error</span>
                            </div>
                            <div className="p-3">
                              <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                                {interaction.error_message}
                              </pre>
                            </div>
                          </div>
                        )}

                        {/* 调试信息 */}
                        {showDebugInfo && interaction.raw_response && (
                          <div className="border border-gray-200 rounded">
                            <div className="flex items-center px-3 py-2 bg-gray-100 border-b border-gray-200">
                              <span className="text-sm font-medium text-gray-700">Raw Response</span>
                            </div>
                            <div className="p-3">
                              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-gray-900 text-green-400 rounded p-2 max-h-32 overflow-y-auto">
                                {JSON.stringify(interaction.raw_response, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default LLMIODisplay;