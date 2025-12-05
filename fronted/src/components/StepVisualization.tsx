import React, { useState, useEffect, useRef } from 'react';
import { ChevronRight, ChevronDown, Play, Pause, CheckCircle, XCircle, Clock, AlertCircle, SkipForward, RotateCcw, Info } from 'lucide-react';

interface StepExecution {
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
}

interface VisualStep {
  id: number;
  name: string;
  step_type: string;
  description?: string;
  order: number;
  executions: StepExecution[];
  children?: VisualStep[];
  parent_id?: number;
  is_loop?: boolean;
  is_condition?: boolean;
  condition_result?: boolean;
  loop_count?: number;
}

interface FlowVisualizationData {
  session_id: number;
  flow_template_id: number;
  current_step_id?: number;
  session_status: string;
  total_steps: number;
  completed_steps: number;
  steps: VisualStep[];
}

interface StepVisualizationProps {
  sessionId: number;
  data: FlowVisualizationData;
  onStepClick?: (step: VisualStep) => void;
  onStepHover?: (step: VisualStep | null) => void;
  compact?: boolean;
  showTimeline?: boolean;
  showPerformance?: boolean;
  interactive?: boolean;
  autoRefresh?: boolean;
}

const StepVisualization: React.FC<StepVisualizationProps> = ({
  sessionId,
  data,
  onStepClick,
  onStepHover,
  compact = false,
  showTimeline = true,
  showPerformance = true,
  interactive = true,
  autoRefresh = false
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [selectedStep, setSelectedStep] = useState<VisualStep | null>(null);
  const [hoveredStep, setHoveredStep] = useState<VisualStep | null>(null);
  const [viewMode, setViewMode] = useState<'flow' | 'timeline' | 'tree'>('flow');
  const svgRef = useRef<SVGSVGElement>(null);

  // 获取步骤状态
  const getStepStatus = (step: VisualStep): StepExecution['status'] => {
    if (step.executions.length === 0) return 'pending';
    return step.executions[step.executions.length - 1].status;
  };

  // 获取状态图标
  const getStatusIcon = (status: StepExecution['status'], size: number = 16) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={size} className="text-green-500" />;
      case 'running':
        return <Clock size={size} className="text-blue-500 animate-pulse" />;
      case 'failed':
        return <XCircle size={size} className="text-red-500" />;
      case 'skipped':
        return <SkipForward size={size} className="text-yellow-500" />;
      case 'timeout':
        return <XCircle size={size} className="text-orange-500" />;
      default:
        return <Clock size={size} className="text-gray-400" />;
    }
  };

  // 获取步骤类型颜色
  const getStepTypeColor = (stepType: string) => {
    switch (stepType.toLowerCase()) {
      case 'start':
        return 'bg-green-100 border-green-300 text-green-800';
      case 'end':
        return 'bg-red-100 border-red-300 text-red-800';
      case 'dialogue':
        return 'bg-blue-100 border-blue-300 text-blue-800';
      case 'condition':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800';
      case 'loop':
        return 'bg-purple-100 border-purple-300 text-purple-800';
      case 'wait':
        return 'bg-gray-100 border-gray-300 text-gray-800';
      case 'parallel':
        return 'bg-indigo-100 border-indigo-300 text-indigo-800';
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800';
    }
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

  // 处理步骤点击
  const handleStepClick = (step: VisualStep) => {
    if (!interactive) return;

    setSelectedStep(step);
    if (onStepClick) {
      onStepClick(step);
    }
  };

  // 处理步骤悬停
  const handleStepHover = (step: VisualStep | null) => {
    setHoveredStep(step);
    if (onStepHover) {
      onStepHover(step);
    }
  };

  // 格式化持续时间
  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return 'N/A';
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  // 计算性能统计
  const getPerformanceStats = () => {
    const allExecutions = data.steps.flatMap(step => step.executions);
    const completedExecutions = allExecutions.filter(exec => exec.status === 'completed');
    const totalDuration = completedExecutions.reduce((sum, exec) => sum + (exec.duration_ms || 0), 0);
    const avgDuration = completedExecutions.length > 0 ? totalDuration / completedExecutions.length : 0;

    return {
      totalSteps: data.steps.length,
      completedSteps: data.completed_steps,
      totalDuration,
      avgDuration,
      successRate: data.total_steps > 0 ? (data.completed_steps / data.total_steps) * 100 : 0
    };
  };

  // 渲染流程图视图
  const renderFlowView = () => {
    const steps = data.steps.sort((a, b) => a.order - b.order);
    const cols = Math.ceil(Math.sqrt(steps.length));
    const rows = Math.ceil(steps.length / cols);

    return (
      <div className="p-4">
        <svg
          ref={svgRef}
          width="100%"
          height={rows * 120}
          className="border border-gray-200 rounded"
        >
          {/* 绘制连接线 */}
          {steps.map((step, index) => {
            if (index === steps.length - 1) return null;

            const currentX = (index % cols) * 200 + 100;
            const currentY = Math.floor(index / cols) * 120 + 60;
            const nextX = ((index + 1) % cols) * 200 + 100;
            const nextY = Math.floor((index + 1) / cols) * 120 + 60;

            const isCurrentStep = data.current_step_id === step.id;

            return (
              <g key={`line-${step.id}`}>
                <line
                  x1={currentX}
                  y1={currentY}
                  x2={nextX}
                  y2={nextY}
                  stroke={isCurrentStep ? '#3B82F6' : '#D1D5DB'}
                  strokeWidth={isCurrentStep ? 3 : 2}
                  markerEnd="url(#arrowhead)"
                />
              </g>
            );
          })}

          {/* 定义箭头 */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="#6B7280"
              />
            </marker>
          </defs>

          {/* 绘制步骤节点 */}
          {steps.map((step, index) => {
            const x = (index % cols) * 200 + 100;
            const y = Math.floor(index / cols) * 120 + 60;
            const status = getStepStatus(step);
            const isCurrentStep = data.current_step_id === step.id;
            const isSelected = selectedStep?.id === step.id;

            return (
              <g
                key={step.id}
                onClick={() => handleStepClick(step)}
                onMouseEnter={() => handleStepHover(step)}
                onMouseLeave={() => handleStepHover(null)}
                className={`cursor-pointer transition-all ${interactive ? '' : 'pointer-events-none'}`}
              >
                {/* 步骤背景 */}
                <rect
                  x={x - 80}
                  y={y - 40}
                  width={160}
                  height={80}
                  rx={8}
                  className={`fill-white border-2 transition-all ${
                    isCurrentStep ? 'border-blue-500 shadow-lg' :
                    isSelected ? 'border-purple-500 shadow-md' :
                    'border-gray-300'
                  } ${interactive ? 'hover:border-blue-400 hover:shadow-md' : ''}`}
                />

                {/* 状态图标 */}
                <foreignObject x={x - 60} y={y - 25} width={24} height={24}>
                  <div className="flex items-center justify-center">
                    {getStatusIcon(status)}
                  </div>
                </foreignObject>

                {/* 步骤名称 */}
                <foreignObject x={x - 30} y={y - 25} width={110} height={20}>
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {step.name}
                  </div>
                </foreignObject>

                {/* 步骤类型 */}
                <foreignObject x={x - 70} y={y} width={140} height={20}>
                  <div className={`text-xs px-2 py-1 rounded-full text-center ${getStepTypeColor(step.step_type)}`}>
                    {step.step_type}
                  </div>
                </foreignObject>

                {/* 执行信息 */}
                {step.executions.length > 0 && (
                  <foreignObject x={x - 70} y={y + 20} width={140} height={15}>
                    <div className="text-xs text-gray-500 text-center">
                      {step.executions.length} execution(s)
                      {step.executions[step.executions.length - 1].duration_ms && (
                        <span> • {formatDuration(step.executions[step.executions.length - 1].duration_ms)}</span>
                      )}
                    </div>
                  </foreignObject>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  // 渲染时间线视图
  const renderTimelineView = () => {
    const allExecutions = data.steps.flatMap(step =>
      step.executions.map(exec => ({ ...exec, step }))
    ).sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

    return (
      <div className="p-4">
        <div className="relative">
          {/* 时间轴主线 */}
          <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-300" />

          {allExecutions.map((execution, index) => {
            const isCurrentStep = data.current_step_id === execution.step.id;

            return (
              <div
                key={`${execution.step.id}-${execution.log_id}`}
                className="relative flex items-start mb-6"
              >
                {/* 时间点 */}
                <div className={`absolute left-6 w-5 h-5 rounded-full border-2 bg-white z-10 ${
                  isCurrentStep ? 'border-blue-500' : 'border-gray-300'
                }`}>
                  <div className="w-full h-full flex items-center justify-center">
                    {getStatusIcon(execution.status, 12)}
                  </div>
                </div>

                {/* 内容 */}
                <div
                  className={`ml-16 p-4 rounded-lg border transition-all ${
                    isCurrentStep ? 'border-blue-500 bg-blue-50' :
                    selectedStep?.id === execution.step.id ? 'border-purple-500 bg-purple-50' :
                    'border-gray-200 bg-white'
                  } ${interactive ? 'cursor-pointer hover:shadow-md' : ''}`}
                  onClick={() => handleStepClick(execution.step)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h4 className="font-medium text-gray-900">{execution.step.name}</h4>
                      <p className="text-sm text-gray-600">{execution.step.step_type}</p>
                    </div>
                    <div className="text-right">
                      <div className={`px-2 py-1 text-xs rounded-full ${getStepTypeColor(execution.step.step_type)}`}>
                        {execution.status}
                      </div>
                      {execution.duration_ms && (
                        <div className="text-xs text-gray-500 mt-1">
                          {formatDuration(execution.duration_ms)}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-xs text-gray-500">
                    {new Date(execution.created_at).toLocaleString()}
                    {execution.started_at && ` • Started: ${new Date(execution.started_at).toLocaleTimeString()}`}
                    {execution.completed_at && ` • Completed: ${new Date(execution.completed_at).toLocaleTimeString()}`}
                  </div>

                  {execution.error_message && (
                    <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-sm text-red-700">
                      {execution.error_message}
                    </div>
                  )}

                  {execution.loop_iteration > 0 && (
                    <div className="mt-1 text-xs text-purple-600">
                      Loop iteration {execution.loop_iteration}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 渲染树形视图
  const renderTreeView = (steps: VisualStep[], level: number = 0) => {
    return (
      <div className={`${level > 0 ? 'ml-6' : ''}`}>
        {steps.map((step) => {
          const status = getStepStatus(step);
          const isExpanded = expandedSteps.has(step.id);
          const isCurrentStep = data.current_step_id === step.id;
          const hasChildren = step.children && step.children.length > 0;

          return (
            <div key={step.id} className="mb-2">
              <div
                className={`flex items-center p-3 rounded-lg border transition-all ${
                  isCurrentStep ? 'border-blue-500 bg-blue-50' :
                  selectedStep?.id === step.id ? 'border-purple-500 bg-purple-50' :
                  'border-gray-200 bg-white'
                } ${interactive ? 'cursor-pointer hover:shadow-md' : ''}`}
                onClick={() => handleStepClick(step)}
              >
                {/* 展开/折叠按钮 */}
                {hasChildren && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleStepExpanded(step.id);
                    }}
                    className="mr-2 text-gray-400 hover:text-gray-600"
                  >
                    {isExpanded ? (
                      <ChevronDown size={16} />
                    ) : (
                      <ChevronRight size={16} />
                    )}
                  </button>
                )}

                {/* 缩进占位符 */}
                {!hasChildren && <div className="w-6 mr-2" />}

                {/* 状态图标 */}
                <div className="mr-3">
                  {getStatusIcon(status)}
                </div>

                {/* 步骤信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <span className="font-medium text-gray-900 truncate">
                      {step.name}
                    </span>
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${getStepTypeColor(step.step_type)}`}>
                      {step.step_type}
                    </span>
                    {isCurrentStep && (
                      <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full">
                        Current
                      </span>
                    )}
                  </div>

                  {step.description && (
                    <p className="text-sm text-gray-600 mt-1 line-clamp-1">
                      {step.description}
                    </p>
                  )}

                  {/* 执行统计 */}
                  <div className="flex items-center mt-1 text-xs text-gray-500">
                    {step.executions.length > 0 && (
                      <>
                        <span>{step.executions.length} execution(s)</span>
                        {step.executions[step.executions.length - 1].duration_ms && (
                          <span className="ml-2">
                            {formatDuration(step.executions[step.executions.length - 1].duration_ms)}
                          </span>
                        )}
                      </>
                    )}
                    {step.is_loop && step.loop_count && (
                      <span className="ml-2 text-purple-600">
                        Loop: {step.loop_count} iterations
                      </span>
                    )}
                    {step.is_condition && step.condition_result !== undefined && (
                      <span className={`ml-2 ${step.condition_result ? 'text-green-600' : 'text-red-600'}`}>
                        Condition: {step.condition_result ? 'True' : 'False'}
                      </span>
                    )}
                  </div>
                </div>

                {/* 性能指标 */}
                {showPerformance && step.executions.length > 0 && (
                  <div className="ml-4 text-right">
                    <div className="text-xs text-gray-500">
                      {step.executions[step.executions.length - 1].duration_ms && (
                        <span>{formatDuration(step.executions[step.executions.length - 1].duration_ms)}</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      {step.executions.length > 1 && `${step.executions.length} runs`}
                    </div>
                  </div>
                )}
              </div>

              {/* 子步骤 */}
              {hasChildren && isExpanded && step.children && (
                <div className="mt-2">
                  {renderTreeView(step.children, level + 1)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const stats = getPerformanceStats();

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* 头部控制 */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Step Visualization</h2>
            <p className="text-sm text-gray-600">
              Session {sessionId} • {data.total_steps} steps
            </p>
          </div>

          {/* 视图切换 */}
          <div className="flex items-center space-x-2">
            {interactive && (
              <>
                <button
                  onClick={() => setViewMode('flow')}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    viewMode === 'flow'
                      ? 'bg-blue-100 text-blue-700 border-blue-300'
                      : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                  } border`}
                >
                  Flow
                </button>
                <button
                  onClick={() => setViewMode('timeline')}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    viewMode === 'timeline'
                      ? 'bg-blue-100 text-blue-700 border-blue-300'
                      : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                  } border`}
                >
                  Timeline
                </button>
                <button
                  onClick={() => setViewMode('tree')}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    viewMode === 'tree'
                      ? 'bg-blue-100 text-blue-700 border-blue-300'
                      : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                  } border`}
                >
                  Tree
                </button>
              </>
            )}
          </div>
        </div>

        {/* 性能统计 */}
        {showPerformance && (
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-blue-600">
                {stats.totalSteps}
              </div>
              <div className="text-xs text-gray-500">Total Steps</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-green-600">
                {stats.completedSteps}
              </div>
              <div className="text-xs text-gray-500">Completed</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-purple-600">
                {formatDuration(stats.totalDuration)}
              </div>
              <div className="text-xs text-gray-500">Total Time</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-orange-600">
                {stats.successRate.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500">Success Rate</div>
            </div>
          </div>
        )}
      </div>

      {/* 视图内容 */}
      <div className="min-h-[400px]">
        {viewMode === 'flow' && renderFlowView()}
        {viewMode === 'timeline' && renderTimelineView()}
        {viewMode === 'tree' && (
          <div className="p-4">
            {renderTreeView(data.steps)}
          </div>
        )}
      </div>

      {/* 底部信息 */}
      {hoveredStep && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <div className="flex items-center text-sm">
            <Info className="w-4 h-4 mr-2 text-blue-500" />
            <span className="font-medium text-gray-700">{hoveredStep.name}</span>
            <span className="ml-2 text-gray-500">• {hoveredStep.step_type}</span>
            <span className="ml-2 text-gray-500">• Order: {hoveredStep.order}</span>
            {hoveredStep.description && (
              <span className="ml-2 text-gray-600">• {hoveredStep.description}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StepVisualization;