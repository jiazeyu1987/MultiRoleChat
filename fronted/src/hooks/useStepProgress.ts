import { useState, useEffect, useCallback, useRef } from 'react';

interface StepInfo {
  id: number;
  name: string;
  step_type: string;
  description?: string;
  order: number;
  executions: Array<{
    log_id: number;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'timeout';
    result_type?: string;
    round_index: number;
    loop_iteration: number;
    attempt_count: number;
    duration_ms?: number;
    error_message?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
  }>;
}

interface FlowVisualizationData {
  session_id: number;
  current_step_id?: number;
  session_status: string;
  total_steps: number;
  completed_steps: number;
  steps: StepInfo[];
}

interface StepProgressSummary {
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  running_steps: number;
  pending_steps: number;
  current_step?: any;
  progress_percentage: number;
}

interface StepProgressData {
  logs: any[];
  summary: StepProgressSummary;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
}

interface UseStepProgressOptions {
  sessionId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  includeDetails?: boolean;
  page?: number;
  perPage?: number;
  enableRealtime?: boolean;
}

interface UseStepProgressReturn {
  flowData: FlowVisualizationData | null;
  progressData: StepProgressData | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  setPage: (page: number) => void;
  currentPage: number;
  totalPages: number;
  hasMore: boolean;
  refreshInterval: number;
  setRefreshInterval: (interval: number) => void;
  toggleAutoRefresh: () => void;
  isAutoRefreshing: boolean;
}

export const useStepProgress = ({
  sessionId,
  autoRefresh = true,
  refreshInterval = 3000,
  includeDetails = false,
  page = 1,
  perPage = 50,
  enableRealtime = true
}: UseStepProgressOptions): UseStepProgressReturn => {
  const [flowData, setFlowData] = useState<FlowVisualizationData | null>(null);
  const [progressData, setProgressData] = useState<StepProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(page);
  const [currentRefreshInterval, setCurrentRefreshInterval] = useState(refreshInterval);
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(autoRefresh);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

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
  }, []);

  // 获取步骤进度数据
  const fetchStepProgress = useCallback(async () => {
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

      const [progressResponse, flowResponse] = await Promise.all([
        fetch(`/api/sessions/${sessionId}/step-progress?${params}`, {
          signal: abortControllerRef.current.signal
        }),
        fetch(`/api/sessions/${sessionId}/flow-visualization`, {
          signal: abortControllerRef.current.signal
        })
      ]);

      // 检查响应状态
      if (!progressResponse.ok || !flowResponse.ok) {
        throw new Error('Failed to fetch step progress data');
      }

      const progressResult = await progressResponse.json();
      const flowResult = await flowResponse.json();

      if (progressResult.success) {
        setProgressData(progressResult.data);
      } else {
        throw new Error(progressResult.message || 'Progress API error');
      }

      if (flowResult.success) {
        setFlowData(flowResult.data);
      } else {
        throw new Error(flowResult.message || 'Flow API error');
      }

      setError(null);
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
        console.error('Error fetching step progress:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId, includeDetails, currentPage, perPage]);

  // 设置实时更新
  const setupRealtimeUpdates = useCallback(() => {
    if (!enableRealtime || eventSourceRef.current) return;

    try {
      const source = new EventSource(`/api/sessions/${sessionId}/live`);

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.event) {
            case 'step_started':
            case 'step_completed':
            case 'step_failed':
            case 'session_progress_updated':
              // 实时更新进度数据
              fetchStepProgress();
              break;
            case 'connected':
              console.log('Real-time connection established');
              break;
            case 'heartbeat':
              // 心跳包，忽略
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
  }, [enableRealtime, sessionId, fetchStepProgress]);

  // 手动刷新数据
  const refetch = useCallback(async () => {
    setLoading(true);
    await fetchStepProgress();
  }, [fetchStepProgress]);

  // 设置页面
  const setPage = useCallback((newPage: number) => {
    if (newPage !== currentPage) {
      setCurrentPage(newPage);
    }
  }, [currentPage]);

  // 设置刷新间隔
  const setRefreshInterval = useCallback((interval: number) => {
    setCurrentRefreshInterval(interval);
  }, []);

  // 切换自动刷新
  const toggleAutoRefresh = useCallback(() => {
    setIsAutoRefreshing(prev => !prev);
  }, []);

  // 计算总页数
  const totalPages = progressData?.pagination.pages || 1;
  const hasMore = progressData?.pagination.has_next || false;

  // 设置自动刷新定时器
  useEffect(() => {
    if (isAutoRefreshing && currentRefreshInterval > 0) {
      intervalRef.current = setInterval(fetchStepProgress, currentRefreshInterval);
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
  }, [isAutoRefreshing, currentRefreshInterval, fetchStepProgress]);

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
    fetchStepProgress();
  }, [fetchStepProgress]);

  // 清理资源
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    flowData,
    progressData,
    loading,
    error,
    refetch,
    setPage,
    currentPage,
    totalPages,
    hasMore,
    refreshInterval: currentRefreshInterval,
    setRefreshInterval,
    toggleAutoRefresh,
    isAutoRefreshing
  };
};

// 辅助 hooks

/**
 * 获取步骤执行统计信息
 */
export const useStepStatistics = (sessionId: number) => {
  const [statistics, setStatistics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatistics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/sessions/${sessionId}/execution-statistics`);

      if (!response.ok) {
        throw new Error('Failed to fetch step statistics');
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
  }, [sessionId]);

  useEffect(() => {
    fetchStatistics();
  }, [fetchStatistics]);

  return { statistics, loading, error, refetch: fetchStatistics };
};

/**
 * 获取活跃会话的进度信息
 */
export const useActiveSessionsProgress = () => {
  const [activeSessions, setActiveSessions] = useState<any[]>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveSessions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/sessions/active-progress');

      if (!response.ok) {
        throw new Error('Failed to fetch active sessions');
      }

      const result = await response.json();
      if (result.success) {
        setActiveSessions(result.data);
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
    fetchActiveSessions();
  }, [fetchActiveSessions]);

  return { activeSessions, loading, error, refetch: fetchActiveSessions };
};

/**
 * 获取步骤进度指标
 */
export const useStepProgressMetrics = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/step-progress/metrics');

      if (!response.ok) {
        throw new Error('Failed to fetch step progress metrics');
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

export default useStepProgress;