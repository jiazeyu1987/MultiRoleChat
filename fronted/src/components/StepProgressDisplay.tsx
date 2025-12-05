import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, XCircle, AlertCircle, Play, RefreshCw, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';

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

interface StepProgressDisplayProps {
  sessionId: number;
  compact?: boolean;
  showDetails?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onStepClick?: (step: StepInfo) => void;
}

interface FlowVisualizationData {
  session_id: number;
  current_step_id?: number;
  session_status: string;
  total_steps: number;
  completed_steps: number;
  steps: StepInfo[];
}

interface StepProgressData {
  logs: any[];
  summary: {
    total_steps: number;
    completed_steps: number;
    failed_steps: number;
    running_steps: number;
    pending_steps: number;
    current_step?: any;
    progress_percentage: number;
  };
  pagination: any;
}

const StepProgressDisplay: React.FC<StepProgressDisplayProps> = ({
  sessionId,
  compact = false,
  showDetails = true,
  autoRefresh = true,
  refreshInterval = 3000,
  onStepClick
}) => {
  const [flowData, setFlowData] = useState<FlowVisualizationData | null>(null);
  const [progressData, setProgressData] = useState<StepProgressData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [selectedStep, setSelectedStep] = useState<StepInfo | null>(null);

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'running':
        return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
      case 'skipped':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
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
      case 'running':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'pending':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'skipped':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'timeout':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // 格式化时间
  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return 'N/A';
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  // 获取最新执行状态
  const getLatestExecutionStatus = (step: StepInfo) => {
    if (step.executions.length === 0) return 'pending';
    return step.executions[step.executions.length - 1].status;
  };

  // 切换步骤展开状态
  const toggleStepExpanded = (stepId: number) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  // 获取进度数据
  const fetchProgressData = async () => {
    try {
      const [progressResponse, flowResponse] = await Promise.all([
        fetch(`/api/sessions/${sessionId}/step-progress?include_details=true`),
        fetch(`/api/sessions/${sessionId}/flow-visualization`)
      ]);

      if (!progressResponse.ok || !flowResponse.ok) {
        throw new Error('Failed to fetch progress data');
      }

      const progressResult = await progressResponse.json();
      const flowResult = await flowResponse.json();

      if (progressResult.success) {
        setProgressData(progressResult.data);
      }

      if (flowResult.success) {
        setFlowData(flowResult.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载数据
  useEffect(() => {
    fetchProgressData();
  }, [sessionId]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchProgressData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, sessionId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        <span>Loading step progress...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
        <div className="flex items-center">
          <XCircle className="w-5 h-5 text-red-500 mr-2" />
          <span className="text-red-700">Error loading progress: {error}</span>
        </div>
      </div>
    );
  }

  if (!flowData || !progressData) {
    return (
      <div className="p-4 border border-gray-200 bg-gray-50 rounded-lg">
        <span className="text-gray-600">No progress data available</span>
      </div>
    );
  }

  // 渲染紧凑视图
  if (compact) {
    return (
      <div className="p-4 border border-gray-200 rounded-lg bg-white">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Flow Progress</h3>
          <span className="text-xs text-gray-500">
            {progressData.summary.completed_steps}/{progressData.summary.total_steps} steps
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progressData.summary.progress_percentage}%` }}
          />
        </div>

        <div className="flex items-center text-xs text-gray-600">
          <Clock className="w-3 h-3 mr-1" />
          <span>
            {progressData.summary.running_steps > 0 && (
              <span className="text-blue-600">{progressData.summary.running_steps} running</span>
            )}
            {progressData.summary.failed_steps > 0 && (
              <span className="text-red-600 ml-2">{progressData.summary.failed_steps} failed</span>
            )}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* 头部信息 */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Step Progress</h2>
            <p className="text-sm text-gray-600">
              Session {sessionId} • {flowData.session_status}
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">
              {progressData.summary.progress_percentage.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">
              {progressData.summary.completed_steps}/{progressData.summary.total_steps} completed
            </div>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progressData.summary.progress_percentage}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>{progressData.summary.completed_steps} completed</span>
            <span>{progressData.summary.running_steps} running</span>
            <span>{progressData.summary.pending_steps} pending</span>
            {progressData.summary.failed_steps > 0 && (
              <span className="text-red-600">{progressData.summary.failed_steps} failed</span>
            )}
          </div>
        </div>
      </div>

      {/* 步骤列表 */}
      <div className="max-h-96 overflow-y-auto">
        {flowData.steps.map((step, index) => {
          const isExpanded = expandedSteps.has(step.id);
          const isSelected = selectedStep?.id === step.id;
          const isCurrentStep = flowData.current_step_id === step.id;
          const latestStatus = getLatestExecutionStatus(step);

          return (
            <div key={step.id} className="border-b border-gray-100 last:border-b-0">
              <div
                className={`px-6 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                  isSelected ? 'bg-blue-50' : ''
                } ${isCurrentStep ? 'border-l-4 border-l-blue-500' : ''}`}
                onClick={() => {
                  if (onStepClick) {
                    onStepClick(step);
                  }
                  setSelectedStep(step);
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center flex-1 min-w-0">
                    {/* 展开/折叠按钮 */}
                    {step.executions.length > 0 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleStepExpanded(step.id);
                        }}
                        className="mr-2 text-gray-400 hover:text-gray-600"
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>
                    )}

                    {/* 状态图标 */}
                    <div className="mr-3">
                      {getStatusIcon(latestStatus)}
                    </div>

                    {/* 步骤信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-gray-900 truncate">
                          {index + 1}. {step.name}
                        </span>
                        {isCurrentStep && (
                          <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="flex items-center mt-1 text-xs text-gray-500">
                        <span className="mr-3">{step.step_type}</span>
                        {step.executions.length > 0 && (
                          <span className="mr-3">
                            {step.executions.length} execution{step.executions.length !== 1 ? 's' : ''}
                          </span>
                        )}
                        {step.executions.length > 0 && step.executions[step.executions.length - 1].duration_ms && (
                          <span>
                            {formatDuration(step.executions[step.executions.length - 1].duration_ms)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 状态标签 */}
                  <div className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(latestStatus)}`}>
                    {latestStatus}
                  </div>
                </div>

                {/* 描述 */}
                {step.description && !compact && (
                  <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                    {step.description}
                  </p>
                )}
              </div>

              {/* 展开的执行详情 */}
              {isExpanded && showDetails && step.executions.length > 0 && (
                <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
                  <div className="text-xs font-medium text-gray-700 mb-2">Execution History</div>
                  <div className="space-y-2">
                    {step.executions.map((execution, execIndex) => (
                      <div key={execution.log_id} className="flex items-center justify-between text-xs">
                        <div className="flex items-center">
                          {getStatusIcon(execution.status)}
                          <span className="ml-2 text-gray-600">
                            Round {execution.round_index}, Attempt {execution.attempt_count}
                          </span>
                          {execution.loop_iteration > 0 && (
                            <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                              Loop {execution.loop_iteration}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center text-gray-500">
                          {execution.duration_ms && (
                            <span className="mr-3">{formatDuration(execution.duration_ms)}</span>
                          )}
                          <span>
                            {new Date(execution.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* 错误信息 */}
                  {step.executions.some(exec => exec.error_message) && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                      <div className="text-xs font-medium text-red-700 mb-1">Recent Error:</div>
                      <div className="text-xs text-red-600">
                        {step.executions
                          .filter(exec => exec.error_message)
                          .slice(-1)[0]?.error_message}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 底部统计 */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div>
            Total: {flowData.total_steps} steps •
            Completed: {progressData.summary.completed_steps} •
            Failed: {progressData.summary.failed_steps}
          </div>
          <div className="flex items-center">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            {autoRefresh ? `Auto-refresh (${refreshInterval/1000}s)` : 'Manual refresh'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StepProgressDisplay;