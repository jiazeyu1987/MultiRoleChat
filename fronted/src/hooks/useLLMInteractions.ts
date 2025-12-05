import { useState, useEffect, useCallback, useRef } from 'react';

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

interface LLMInteractionStatistics {
  total_interactions: number;
  completed_interactions: number;
  failed_interactions: number;
  active_interactions: number;
  success_rate: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  average_latency_ms: number;
}

interface LLMInteractionData {
  interactions: LLMInteraction[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
  statistics: LLMInteractionStatistics;
}

interface UseLLMInteractionsOptions {
  sessionId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  includeDetails?: boolean;
  page?: number;
  perPage?: number;
  statusFilter?: 'all' | 'pending' | 'streaming' | 'completed' | 'failed' | 'timeout';
  enableRealtime?: boolean;
}

interface UseLLMInteractionsReturn {
  interactions: LLMInteraction[];
  statistics: LLMInteractionStatistics | null;
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  } | null;
  refetch: () => Promise<void>;
  setPage: (page: number) => void;
  setFilter: (filter: string) => void;
  currentPage: number;
  totalPages: number;
  hasMore: boolean;
  currentFilter: string;
  refreshInterval: number;
  setRefreshInterval: (interval: number) => void;
  toggleAutoRefresh: () => void;
  isAutoRefreshing: boolean;
  exportData: () => void;
}

export const useLLMInteractions = ({
  sessionId,
  autoRefresh = true,
  refreshInterval = 3000,
  includeDetails = false,
  page = 1,
  perPage = 50,
  statusFilter = 'all',
  enableRealtime = true
}: UseLLMInteractionsOptions): UseLLMInteractionsReturn => {
  const [interactions, setInteractions] = useState<LLMInteraction[]>([]);
  const [statistics, setStatistics] = useState<LLMInteractionStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(page);
  const [currentFilter, setCurrentFilter] = useState(statusFilter);
  const [currentRefreshInterval, setCurrentRefreshInterval] = useState(refreshInterval);
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(autoRefresh);
  const [pagination, setPagination] = useState<any>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingDataRef = useRef<Map<number, string>>(new Map());

  // 清理函数
  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    streamingDataRef.current.clear();
  }, []);

  // 获取LLM交互数据
  const fetchInteractions = useCallback(async () => {
    try {
      // 取消之前的请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // 创建新的 AbortController
      abortControllerRef.current = new AbortController();

      // 构建请求参数
      const params = new URLSearchParams({
        include_details: includeDetails.toString(),
        page: currentPage.toString(),
        per_page: perPage.toString()
      });

      if (currentFilter !== 'all') {
        params.append('status', currentFilter);
      }

      const response = await fetch(
        `/api/sessions/${sessionId}/llm-interactions?${params}`,
        {
          signal: abortControllerRef.current.signal
        }
      );

      // 检查响应状态
      if (!response.ok) {
        throw new Error('Failed to fetch LLM interactions');
      }

      const result = await response.json();

      if (result.success) {
        setInteractions(result.data.interactions);
        setStatistics(result.data.statistics);
        setPagination(result.data.pagination);
        setError(null);
      } else {
        throw new Error(result.message || 'LLM interactions API error');
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
        console.error('Error fetching LLM interactions:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId, includeDetails, currentPage, perPage, currentFilter]);

  // 设置实时更新
  const setupRealtimeUpdates = useCallback(() => {
    if (!enableRealtime || eventSourceRef.current) return;

    try {
      const source = new EventSource(`/api/sessions/${sessionId}/live`);

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.event) {
            case 'llm_request_started':
              // 处理请求开始
              if (data.interaction_id) {
                setInteractions(prev =>
                  prev.map(interaction =>
                    interaction.id === data.interaction_id
                      ? { ...interaction, status: 'pending' }
                      : interaction
                  )
                );
              }
              break;
            case 'llm_response_streaming':
              // 处理流式响应
              if (data.interaction_id && data.content_chunk) {
                streamingDataRef.current.set(data.interaction_id,
                  (streamingDataRef.current.get(data.interaction_id) || '') + data.content_chunk
                );

                setInteractions(prev =>
                  prev.map(interaction =>
                    interaction.id === data.interaction_id
                      ? { ...interaction, status: 'streaming' }
                      : interaction
                  )
                );
              }
              break;
            case 'llm_response_completed':
              // 响应完成，清除流式内容并重新获取数据
              if (data.interaction_id) {
                streamingDataRef.current.delete(data.interaction_id);
                fetchInteractions();
              }
              break;
            case 'llm_request_failed':
            case 'llm_request_timeout':
              // 请求失败或超时
              if (data.interaction_id) {
                streamingDataRef.current.delete(data.interaction_id);
                fetchInteractions();
              }
              break;
          }
        } catch (err) {
          console.error('Error parsing real-time message:', err);
        }
      };

      source.onerror = (err) => {
        console.error('Real-time connection error:', err);
        source.close();
        eventSourceRef.current = null;

        // 5秒后尝试重连
        setTimeout(() => {
          if (enableRealtime) {
            setupRealtimeUpdates();
          }
        }, 5000);
      };

      eventSourceRef.current = source;
    } catch (err) {
      console.error('Failed to setup real-time updates:', err);
    }
  }, [enableRealtime, sessionId, fetchInteractions]);

  // 手动刷新数据
  const refetch = useCallback(async () => {
    setLoading(true);
    await fetchInteractions();
  }, [fetchInteractions]);

  // 设置页面
  const setPage = useCallback((newPage: number) => {
    if (newPage !== currentPage) {
      setCurrentPage(newPage);
    }
  }, [currentPage]);

  // 设置过滤器
  const setFilter = useCallback((filter: string) => {
    if (filter !== currentFilter) {
      setCurrentFilter(filter);
      setCurrentPage(1); // 重置到第一页
    }
  }, [currentFilter]);

  // 设置刷新间隔
  const setRefreshInterval = useCallback((interval: number) => {
    setCurrentRefreshInterval(interval);
  }, []);

  // 切换自动刷新
  const toggleAutoRefresh = useCallback(() => {
    setIsAutoRefreshing(prev => !prev);
  }, []);

  // 导出数据
  const exportData = useCallback(() => {
    const exportData = {
      session_id: sessionId,
      export_time: new Date().toISOString(),
      filter: currentFilter,
      statistics,
      interactions: interactions.map(interaction => ({
        ...interaction,
        streaming_content: streamingDataRef.current.get(interaction.id)
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `llm_interactions_session_${sessionId}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [sessionId, currentFilter, statistics, interactions]);

  // 获取流式内容
  const getStreamingContent = useCallback((interactionId: number) => {
    return streamingDataRef.current.get(interactionId);
  }, []);

  // 计算总页数
  const totalPages = pagination?.pages || 1;
  const hasMore = pagination?.has_next || false;

  // 设置自动刷新定时器
  useEffect(() => {
    if (isAutoRefreshing && currentRefreshInterval > 0) {
      intervalRef.current = setInterval(fetchInteractions, currentRefreshInterval);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isAutoRefreshing, currentRefreshInterval, fetchInteractions]);

  // 设置实时更新
  useEffect(() => {
    if (enableRealtime) {
      setupRealtimeUpdates();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [enableRealtime, setupRealtimeUpdates]);

  // 初始数据加载
  useEffect(() => {
    fetchInteractions();
  }, [fetchInteractions]);

  // 清理资源
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    interactions,
    statistics,
    loading,
    error,
    pagination,
    refetch,
    setPage,
    setFilter,
    currentPage,
    totalPages,
    hasMore,
    currentFilter,
    refreshInterval: currentRefreshInterval,
    setRefreshInterval,
    toggleAutoRefresh,
    isAutoRefreshing,
    exportData,
    getStreamingContent
  };
};

// 辅助 hooks

/**
 * 获取LLM使用统计信息
 */
export const useLLMStatistics = (sessionId: number, days: number = 7) => {
  const [statistics, setStatistics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatistics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/sessions/${sessionId}/llm-statistics?days=${days}`);

      if (!response.ok) {
        throw new Error('Failed to fetch LLM statistics');
      }

      const result = await response.json();
      if (result.success) {
        setStatistics(result.data);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [sessionId, days]);

  useEffect(() => {
    fetchStatistics();
  }, [fetchStatistics]);

  return { statistics, loading, error, refetch: fetchStatistics };
};

/**
 * 获取活跃的LLM交互
 */
export const useActiveLLMInteractions = () => {
  const [activeInteractions, setActiveInteractions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveInteractions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/llm-interactions/active');

      if (!response.ok) {
        throw new Error('Failed to fetch active LLM interactions');
      }

      const result = await response.json();
      if (result.success) {
        setActiveInteractions(result.data);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActiveInteractions();
  }, [fetchActiveInteractions]);

  return { activeInteractions, loading, error, refetch: fetchActiveInteractions };
};

/**
 * 获取LLM使用趋势
 */
export const useLLMUsageTrends = (days: number = 30) => {
  const [trends, setTrends] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/llm-interactions/trends?days=${days}`);

      if (!response.ok) {
        throw new Error('Failed to fetch LLM usage trends');
      }

      const result = await response.json();
      if (result.success) {
        setTrends(result.data);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchTrends();
  }, [fetchTrends]);

  return { trends, loading, error, refetch: fetchTrends };
};

/**
 * 获取LLM系统指标
 */
export const useLLMSystemMetrics = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/llm-interactions/metrics');

      if (!response.ok) {
        throw new Error('Failed to fetch LLM system metrics');
      }

      const result = await response.json();
      if (result.success) {
        setMetrics(result.data);
      } else {
        throw new Error(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { metrics, loading, error, refetch: fetchMetrics };
};

export default useLLMInteractions;