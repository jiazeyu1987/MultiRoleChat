import React, { useState, useEffect } from 'react';
import {
  Bug,
  Terminal,
  Settings,
  Database,
  Activity,
  AlertTriangle,
  Info,
  Copy,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  X,
  Eye,
  EyeOff,
  Zap,
  Cpu,
  Memory,
  HardDrive
} from 'lucide-react';

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_connections: number;
  total_requests: number;
  error_rate: number;
  avg_response_time: number;
  uptime: number;
}

interface DebugEvent {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  event_type: string;
  session_id?: number;
  message: string;
  data?: any;
  stack_trace?: string;
}

interface PerformanceMetrics {
  step_executions: {
    total: number;
    successful: number;
    failed: number;
    avg_duration: number;
  };
  llm_calls: {
    total: number;
    successful: number;
    failed: number;
    avg_latency: number;
    total_tokens: number;
  };
  database_queries: {
    total: number;
    avg_duration: number;
    slow_queries: number;
  };
}

interface DebugPanelProps {
  sessionId?: number;
  visible: boolean;
  onClose: () => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
  showAdvanced?: boolean;
  position?: 'fixed' | 'relative';
  size?: 'small' | 'medium' | 'large';
}

const DebugPanel: React.FC<DebugPanelProps> = ({
  sessionId,
  visible,
  onClose,
  autoRefresh = true,
  refreshInterval = 2000,
  showAdvanced = false,
  position = 'fixed',
  size = 'medium'
}) => {
  const [activeTab, setActiveTab] = useState<'events' | 'metrics' | 'system' | 'logs'>('events');
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [selectedEventLevel, setSelectedEventLevel] = useState<string>('all');
  const [isRealtime, setIsRealtime] = useState(true);
  const [showRawData, setShowRawData] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // 获取面板尺寸类
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'w-96 h-80';
      case 'medium':
        return 'w-[600px] h-[500px]';
      case 'large':
        return 'w-[800px] h-[600px]';
      default:
        return 'w-[600px] h-[500px]';
    }
  };

  // 获取位置类
  const getPositionClasses = () => {
    if (position === 'fixed') {
      return 'fixed bottom-4 right-4 z-50';
    }
    return 'relative';
  };

  // 过滤事件
  const filteredEvents = events.filter(event => {
    const matchesLevel = selectedEventLevel === 'all' || event.level === selectedEventLevel;
    const matchesSearch = searchTerm === '' ||
      event.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      event.event_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSession = !sessionId || event.session_id === sessionId;
    return matchesLevel && matchesSearch && matchesSession;
  });

  // 获取事件颜色
  const getEventColor = (level: string) => {
    switch (level) {
      case 'debug':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      case 'info':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'critical':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  // 获取事件图标
  const getEventIcon = (level: string) => {
    switch (level) {
      case 'debug':
        return <Terminal className="w-4 h-4" />;
      case 'info':
        return <Info className="w-4 h-4" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4" />;
      case 'error':
        return <X className="w-4 h-4" />;
      case 'critical':
        return <Bug className="w-4 h-4" />;
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  // 切换事件展开状态
  const toggleEventExpanded = (eventId: string) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedEvents(newExpanded);
  };

  // 复制到剪贴板
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      console.log('Copied to clipboard');
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // 导出调试数据
  const exportDebugData = () => {
    const debugData = {
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      events: filteredEvents,
      system_metrics: systemMetrics,
      performance_metrics: performanceMetrics,
      filters: {
        level: selectedEventLevel,
        search_term: searchTerm
      }
    };

    const blob = new Blob([JSON.stringify(debugData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debug_data_${sessionId || 'system'}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 清除事件
  const clearEvents = () => {
    setEvents([]);
  };

  // 获取调试数据
  const fetchDebugData = async () => {
    try {
      setLoading(true);

      const [systemResponse, performanceResponse] = await Promise.all([
        fetch('/api/monitoring/system-info'),
        fetch(sessionId ? `/api/sessions/${sessionId}/execution-statistics` : '/api/step-progress/metrics')
      ]);

      if (systemResponse.ok) {
        const systemResult = await systemResponse.json();
        if (systemResult.success) {
          setSystemMetrics(systemResult.data);
        }
      }

      if (performanceResponse.ok) {
        const perfResult = await performanceResponse.json();
        if (perfResult.success) {
          setPerformanceMetrics({
            step_executions: perfResult.data,
            llm_calls: perfResult.data,
            database_queries: perfResult.data
          });
        }
      }
    } catch (err) {
      console.error('Failed to fetch debug data:', err);
    } finally {
      setLoading(false);
    }
  };

  // 设置实时事件监听
  const setupRealtimeEvents = () => {
    if (!isRealtime) return;

    try {
      const eventSource = new EventSource('/api/system/live');

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.event === 'error_occurred' || data.event === 'system_status_updated') {
            const debugEvent: DebugEvent = {
              id: `realtime-${Date.now()}`,
              timestamp: data.timestamp,
              level: data.event === 'error_occurred' ? 'error' : 'info',
              event_type: data.event,
              session_id: data.session_id,
              message: data.data?.message || data.data?.error || 'System event',
              data: data.data
            };

            setEvents(prev => [debugEvent, ...prev.slice(0, 99)]); // 保留最新100条
          }
        } catch (err) {
          console.error('Failed to parse debug event:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('Debug SSE error:', err);
        eventSource.close();
      };
    } catch (err) {
      console.error('Failed to setup debug SSE:', err);
    }
  };

  // 初始数据加载
  useEffect(() => {
    fetchDebugData();
    setupRealtimeEvents();
  }, []);

  // 自动刷新
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchDebugData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval]);

  // 模拟一些初始调试事件
  useEffect(() => {
    const initialEvents: DebugEvent[] = [
      {
        id: '1',
        timestamp: new Date().toISOString(),
        level: 'info',
        event_type: 'session_created',
        session_id: sessionId,
        message: sessionId ? `Session ${sessionId} created` : 'Debug panel initialized',
        data: { panel_size: size, auto_refresh: autoRefresh }
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 1000).toISOString(),
        level: 'debug',
        event_type: 'system_check',
        message: 'System health check completed',
        data: { status: 'healthy', services: ['database', 'llm', 'websocket'] }
      }
    ];

    setEvents(initialEvents);
  }, [sessionId, size, autoRefresh]);

  if (!visible) return null;

  return (
    <div className={`${getPositionClasses()}`}>
      <div className={`${getSizeClasses()} bg-white border border-gray-300 rounded-lg shadow-2xl flex flex-col`}>
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <div className="flex items-center">
            <Bug className="w-5 h-5 text-gray-600 mr-2" />
            <h3 className="font-semibold text-gray-900">Debug Panel</h3>
            {sessionId && (
              <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                Session {sessionId}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {/* 实时状态 */}
            <button
              onClick={() => setIsRealtime(!isRealtime)}
              className={`p-1 rounded transition-colors ${
                isRealtime ? 'text-green-600 hover:bg-green-100' : 'text-gray-400 hover:bg-gray-100'
              }`}
              title={isRealtime ? 'Real-time enabled' : 'Real-time disabled'}
            >
              <Zap className="w-4 h-4" />
            </button>

            {/* 刷新按钮 */}
            <button
              onClick={fetchDebugData}
              disabled={loading}
              className="p-1 rounded text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              title="Refresh data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>

            {/* 导出按钮 */}
            <button
              onClick={exportDebugData}
              className="p-1 rounded text-gray-600 hover:bg-gray-100"
              title="Export debug data"
            >
              <Download className="w-4 h-4" />
            </button>

            {/* 关闭按钮 */}
            <button
              onClick={onClose}
              className="p-1 rounded text-gray-600 hover:bg-gray-100"
              title="Close debug panel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 标签页 */}
        <div className="flex border-b border-gray-200">
          {[
            { id: 'events', label: 'Events', icon: <Activity className="w-4 h-4" /> },
            { id: 'metrics', label: 'Metrics', icon: <Database className="w-4 h-4" /> },
            { id: 'system', label: 'System', icon: <Cpu className="w-4 h-4" /> },
            { id: 'logs', label: 'Logs', icon: <Terminal className="w-4 h-4" /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.icon}
              <span className="ml-2">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-hidden">
          {/* 事件标签页 */}
          {activeTab === 'events' && (
            <div className="flex flex-col h-full">
              {/* 过滤器 */}
              <div className="flex items-center space-x-2 p-3 border-b border-gray-200">
                <select
                  value={selectedEventLevel}
                  onChange={(e) => setSelectedEventLevel(e.target.value)}
                  className="px-2 py-1 text-xs border border-gray-300 rounded"
                >
                  <option value="all">All Levels</option>
                  <option value="debug">Debug</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="error">Error</option>
                  <option value="critical">Critical</option>
                </select>

                <input
                  type="text"
                  placeholder="Search events..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded"
                />

                <button
                  onClick={() => setShowRawData(!showRawData)}
                  className="p-1 text-xs text-gray-600 hover:bg-gray-100 rounded"
                  title="Toggle raw data view"
                >
                  {showRawData ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </button>

                <button
                  onClick={clearEvents}
                  className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 border border-red-200 rounded"
                >
                  Clear
                </button>
              </div>

              {/* 事件列表 */}
              <div className="flex-1 overflow-y-auto p-3">
                {filteredEvents.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    No debug events found
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredEvents.map((event) => {
                      const isExpanded = expandedEvents.has(event.id);
                      return (
                        <div
                          key={event.id}
                          className={`border rounded-lg ${getEventColor(event.level)}`}
                        >
                          <div
                            className="flex items-start p-3 cursor-pointer"
                            onClick={() => toggleEventExpanded(event.id)}
                          >
                            <div className="mr-3 mt-0.5">
                              {getEventIcon(event.level)}
                            </div>

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-sm">{event.event_type}</span>
                                <span className="text-xs opacity-75">
                                  {new Date(event.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              <p className="text-sm mt-1">{event.message}</p>
                              {event.session_id && (
                                <span className="text-xs opacity-75">Session: {event.session_id}</span>
                              )}
                            </div>

                            <ChevronDown
                              className={`w-4 h-4 ml-2 transition-transform ${
                                isExpanded ? 'transform rotate-180' : ''
                              }`}
                            />
                          </div>

                          {/* 展开的详细信息 */}
                          {isExpanded && event.data && (
                            <div className="border-t border-gray-200 p-3 bg-black bg-opacity-5">
                              <pre className="text-xs overflow-x-auto whitespace-pre-wrap font-mono">
                                {showRawData
                                  ? JSON.stringify(event.data, null, 2)
                                  : JSON.stringify(event.data, null, 2)
                                }
                              </pre>
                              {event.stack_trace && (
                                <div className="mt-2 p-2 bg-red-100 rounded">
                                  <div className="text-xs font-semibold text-red-700 mb-1">Stack Trace:</div>
                                  <pre className="text-xs text-red-800 font-mono whitespace-pre-wrap">
                                    {event.stack_trace}
                                  </pre>
                                </div>
                              )}
                              <div className="flex justify-end mt-2">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    copyToClipboard(JSON.stringify(event.data, null, 2));
                                  }}
                                  className="p-1 text-xs text-gray-600 hover:bg-gray-200 rounded"
                                >
                                  <Copy className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 指标标签页 */}
          {activeTab === 'metrics' && (
            <div className="p-4 overflow-y-auto">
              {performanceMetrics ? (
                <div className="space-y-6">
                  {/* 步骤执行指标 */}
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Activity className="w-4 h-4 mr-2" />
                      Step Execution Metrics
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-lg font-semibold text-blue-600">
                          {performanceMetrics.step_executions.total}
                        </div>
                        <div className="text-xs text-gray-600">Total Executions</div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="text-lg font-semibold text-green-600">
                          {performanceMetrics.step_executions.successful}
                        </div>
                        <div className="text-xs text-gray-600">Successful</div>
                      </div>
                      <div className="p-3 bg-red-50 rounded-lg">
                        <div className="text-lg font-semibold text-red-600">
                          {performanceMetrics.step_executions.failed}
                        </div>
                        <div className="text-xs text-gray-600">Failed</div>
                      </div>
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <div className="text-lg font-semibold text-purple-600">
                          {(performanceMetrics.step_executions.avg_duration / 1000).toFixed(2)}s
                        </div>
                        <div className="text-xs text-gray-600">Avg Duration</div>
                      </div>
                    </div>
                  </div>

                  {/* LLM调用指标 */}
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Zap className="w-4 h-4 mr-2" />
                      LLM Call Metrics
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-lg font-semibold text-blue-600">
                          {performanceMetrics.llm_calls.total}
                        </div>
                        <div className="text-xs text-gray-600">Total Calls</div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="text-lg font-semibold text-green-600">
                          {performanceMetrics.llm_calls.successful}
                        </div>
                        <div className="text-xs text-gray-600">Successful</div>
                      </div>
                      <div className="p-3 bg-yellow-50 rounded-lg">
                        <div className="text-lg font-semibold text-yellow-600">
                          {performanceMetrics.llm_calls.total_tokens}
                        </div>
                        <div className="text-xs text-gray-600">Total Tokens</div>
                      </div>
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <div className="text-lg font-semibold text-purple-600">
                          {(performanceMetrics.llm_calls.avg_latency / 1000).toFixed(2)}s
                        </div>
                        <div className="text-xs text-gray-600">Avg Latency</div>
                      </div>
                    </div>
                  </div>

                  {/* 数据库查询指标 */}
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Database className="w-4 h-4 mr-2" />
                      Database Query Metrics
                    </h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-lg font-semibold text-blue-600">
                          {performanceMetrics.database_queries.total}
                        </div>
                        <div className="text-xs text-gray-600">Total Queries</div>
                      </div>
                      <div className="p-3 bg-yellow-50 rounded-lg">
                        <div className="text-lg font-semibold text-yellow-600">
                          {performanceMetrics.database_queries.avg_duration}ms
                        </div>
                        <div className="text-xs text-gray-600">Avg Duration</div>
                      </div>
                      <div className="p-3 bg-red-50 rounded-lg">
                        <div className="text-lg font-semibold text-red-600">
                          {performanceMetrics.database_queries.slow_queries}
                        </div>
                        <div className="text-xs text-gray-600">Slow Queries</div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <RefreshCw className="w-6 h-6 animate-spin mr-2" />
                  <span>Loading metrics...</span>
                </div>
              )}
            </div>
          )}

          {/* 系统标签页 */}
          {activeTab === 'system' && (
            <div className="p-4 overflow-y-auto">
              {systemMetrics ? (
                <div className="space-y-6">
                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Cpu className="w-4 h-4 mr-2" />
                      System Resources
                    </h4>
                    <div className="space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">CPU Usage</span>
                          <span className="text-sm font-medium">{systemMetrics.cpu_usage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${systemMetrics.cpu_usage}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Memory Usage</span>
                          <span className="text-sm font-medium">{systemMetrics.memory_usage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${systemMetrics.memory_usage}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Disk Usage</span>
                          <span className="text-sm font-medium">{systemMetrics.disk_usage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-yellow-600 h-2 rounded-full"
                            style={{ width: `${systemMetrics.disk_usage}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Activity className="w-4 h-4 mr-2" />
                      Connection Statistics
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-lg font-semibold text-blue-600">
                          {systemMetrics.active_connections}
                        </div>
                        <div className="text-xs text-gray-600">Active Connections</div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="text-lg font-semibold text-green-600">
                          {systemMetrics.total_requests}
                        </div>
                        <div className="text-xs text-gray-600">Total Requests</div>
                      </div>
                      <div className="p-3 bg-yellow-50 rounded-lg">
                        <div className="text-lg font-semibold text-yellow-600">
                          {systemMetrics.error_rate.toFixed(2)}%
                        </div>
                        <div className="text-xs text-gray-600">Error Rate</div>
                      </div>
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <div className="text-lg font-semibold text-purple-600">
                          {(systemMetrics.avg_response_time / 1000).toFixed(2)}s
                        </div>
                        <div className="text-xs text-gray-600">Avg Response Time</div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <HardDrive className="w-4 h-4 mr-2" />
                      System Information
                    </h4>
                    <div className="bg-gray-50 p-3 rounded-lg">
                      <div className="text-sm space-y-1">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Uptime:</span>
                          <span className="font-medium">{(systemMetrics.uptime / 3600).toFixed(1)} hours</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Auto Refresh:</span>
                          <span className="font-medium">{autoRefresh ? 'Enabled' : 'Disabled'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Real-time:</span>
                          <span className="font-medium">{isRealtime ? 'Enabled' : 'Disabled'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <RefreshCw className="w-6 h-6 animate-spin mr-2" />
                  <span>Loading system metrics...</span>
                </div>
              )}
            </div>
          )}

          {/* 日志标签页 */}
          {activeTab === 'logs' && (
            <div className="p-4">
              <div className="text-center text-gray-500 py-8">
                <Terminal className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p>Advanced logging features coming soon</p>
                <p className="text-sm mt-1">Check the Events tab for real-time debug information</p>
              </div>
            </div>
          )}
        </div>

        {/* 底部状态栏 */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-600">
          <div className="flex items-center space-x-4">
            <span>Events: {filteredEvents.length}</span>
            <span>•</span>
            <span className={isRealtime ? 'text-green-600' : 'text-gray-400'}>
              {isRealtime ? 'Live' : 'Offline'}
            </span>
          </div>
          <div>
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DebugPanel;