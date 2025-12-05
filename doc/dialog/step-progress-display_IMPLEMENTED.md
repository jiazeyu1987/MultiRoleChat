# 步骤进度显示组件实现文档

## 📋 概述

**⚠️ 重要更新**: 本文档基于当前代码实现编写，与原始设计存在差异。

**StepProgressDisplay** 是一个基于执行日志的实时步骤进度显示组件，支持可视化会话执行流程、多视图模式切换和实时更新。

---

## 🎯 核心功能

### 已实现特性

- ✅ **执行日志显示**: 基于 `StepExecutionLog` 的完整执行历史
- ✅ **性能指标**: 执行时间、内存使用、成功率统计
- ✅ **多视图模式**: 紧凑视图和详细视图切换
- ✅ **循环/分支支持**: 完整的条件评估和循环迭代追踪
- ✅ **实时更新**: SSE实时推送进度变化
- ✅ **交互功能**: 点击步骤查看详情
- ✅ **响应式设计**: 支持不同屏幕尺寸

---

## 🏗️ 数据结构

### 实际API响应格式

```typescript
interface StepProgressResponse {
  logs: StepExecutionLog[];    // 执行日志数组
  summary: ExecutionSummary;   // 执行摘要
  current_step?: StepInfo;     // 当前步骤信息 (include_details=true时)
  pagination: PaginationInfo;   // 分页信息
}

interface StepExecutionLog {
  id: number;
  session_id: number;
  step_id: number;
  execution_order: number;
  round_index: number;          // 轮次索引
  loop_iteration: number;       // 循环迭代次数
  attempt_count: number;        // 尝试次数
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'timeout';
  result_type?: string;         // success/condition_true/condition_false/loop_continue/loop_break/error
  result_data?: string;        // 执行结果数据 (JSON)
  condition_evaluation?: boolean; // 条件评估结果
  loop_check_result?: boolean;    // 循环检查结果
  error_message?: string;        // 错误信息
  duration_ms?: number;          // 执行时长 (毫秒)
  memory_usage_mb?: number;       // 内存使用 (MB)
  created_at: string;           // 创建时间
  started_at?: string;          // 开始执行时间
  completed_at?: string;        // 完成时间
  step_snapshot?: string;       // 步骤配置快照 (JSON)
  context_snapshot?: string;    // 执行上下文快照 (JSON)
}

interface ExecutionSummary {
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  running_steps: number;
  progress_percentage: number;
  current_step?: {
    id: number;
    name: string;
    status: string;
  };
  average_duration_ms?: number;
  total_duration_ms?: number;
}

interface StepInfo {
  id: number;
  name: string;
  step_type: string;           // dialogue/condition/loop/end
  description: string;
  order: number;
  executions: Array<{         // 执行历史
    log_id: number;
    status: string;
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
```

### 流程可视化数据

```typescript
interface FlowVisualizationResponse {
  session_id: number;
  flow_template_id: number;
  current_step_id: number;
  session_status: string;
  total_steps: number;
  completed_steps: number;
  steps: Array<{
    id: number;
    name: string;
    step_type: string;
    description: string;
    order: number;
    executions: Array<{
      log_id: number;
      status: string;
      result_type: string;
      round_index: number;
      loop_iteration: number;
      attempt_count: number;
      duration_ms: number;
      error_message: string;
    }>;
  }>;
}
```

---

## 🎨 组件API

### Props接口

```typescript
interface StepProgressDisplayProps {
  sessionId: number;                    // 会话ID (必需)
  compact?: boolean;                     // 紧凑模式 (默认: false)
  showDetails?: boolean;                // 显示详细信息 (默认: true)
  autoRefresh?: boolean;                 // 自动刷新 (默认: true)
  refreshInterval?: number;              // 刷新间隔(ms, 默认: 3000)
  onStepClick?: (step: StepInfo) => void; // 步骤点击回调
}
```

### 实际使用示例

```typescript
// 基础使用
<StepProgressDisplay
  sessionId={sessionId}
  compact={false}
  showDetails={true}
  autoRefresh={true}
  refreshInterval={3000}
  onStepClick={(step) => {
    console.log('Clicked step:', step);
    // 处理步骤点击
  }}
/>

// 紧凑模式 (侧边栏使用)
<StepProgressDisplay
  sessionId={sessionId}
  compact={true}
  showDetails={false}
  autoRefresh={true}
/>

// 详细模式 (主视图使用)
<StepProgressDisplay
  sessionId={sessionId}
  compact={false}
  showDetails={true}
  autoRefresh={true}
  refreshInterval={1000}
/>
```

---

## 🔧 内部实现

### useStepProgress Hook

```typescript
const useStepProgress = ({
  sessionId,
  autoRefresh = true,
  refreshInterval = 3000,
  includeDetails = false
}: UseStepProgressOptions) => {
  const [flowData, setFlowData] = useState<any>(null);
  const [progressData, setProgressData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 同时调用两个API端点
  const fetchStepProgress = async () => {
    try {
      const [progressResponse, flowResponse] = await Promise.all([
        fetch(`/api/sessions/${sessionId}/step-progress?page=1&per_page=50&include_details=${includeDetails}`),
        fetch(`/api/sessions/${sessionId}/flow-visualization`)
      ]);

      setProgressData(await progressResponse.json());
      setFlowData(await flowResponse.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 实时更新集成
  useSessionWebSocket(sessionId, {
    autoConnect: autoRefresh,
    onMessage: (message) => {
      if (message.event === 'step_completed' || message.event === 'step_failed') {
        fetchStepProgress(); // 刷新数据
      }
    }
  });

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchStepProgress, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  return {
    flowData,
    progressData,
    loading,
    error,
    refetch: fetchStepProgress
  };
};
```

### 数据处理逻辑

```typescript
// 处理步骤进度数据
const processStepData = (response: StepProgressResponse) => {
  const { logs, summary, current_step } = response;

  // 生成步骤列表 (从执行日志中提取)
  const stepsMap = new Map<number, StepInfo>();

  logs.forEach(log => {
    if (!stepsMap.has(log.step_id)) {
      stepsMap.set(log.step_id, {
        id: log.step_id,
        name: log.step_name || `步骤 ${log.step_id}`,
        step_type: log.step_type || 'dialogue',
        description: log.step_description || '',
        order: log.execution_order,
        executions: []
      });
    }

    // 添加执行记录
    stepsMap.get(log.step_id)!.executions.push({
      log_id: log.id,
      status: log.status,
      result_type: log.result_type,
      round_index: log.round_index,
      loop_iteration: log.loop_iteration,
      attempt_count: log.attempt_count,
      duration_ms: log.duration_ms,
      error_message: log.error_message,
      created_at: log.created_at,
      started_at: log.started_at,
      completed_at: log.completed_at
    });
  });

  return Array.from(stepsMap.values()).sort((a, b) => a.order - b.order);
};
```

---

## 🎨 UI组件结构

### 紧凑模式 (compact=true)

```typescript
const CompactView = ({ progressData, onStepClick }) => {
  return (
    <div className="step-progress-display compact">
      <div className="progress-header">
        <h3>步骤进度</h3>
        <div className="progress-stats">
          <span>{progressData?.summary?.completed_steps || 0}/{progressData?.summary?.total_steps || 0}</span>
          <span>{progressData?.summary?.progress_percentage?.toFixed(1) || 0}%</span>
        </div>
      </div>

      <div className="progress-list">
        {progressData?.logs?.map(log => (
          <div
            key={log.id}
            className={`step-item ${log.status}`}
            onClick={() => onStepClick(log)}
          >
            <StatusIcon status={log.status} />
            <span className="step-name">{log.step_name}</span>
            <span className="step-order">#{log.execution_order}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 详细模式 (compact=false)

```typescript
const DetailedView = ({ progressData, onStepClick }) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  return (
    <div className="step-progress-display detailed">
      <div className="progress-header">
        <h3>执行进度详情</h3>
        <div className="progress-controls">
          <RefreshButton onClick={() => {}} />
          <ExportButton onClick={() => {}} />
        </div>
      </div>

      <div className="progress-summary">
        <div className="summary-item">
          <label>总步骤:</label>
          <span>{progressData?.summary?.total_steps}</span>
        </div>
        <div className="summary-item">
          <label>已完成:</label>
          <span>{progressData?.summary?.completed_steps}</span>
        </div>
        <div className="summary-item">
          <label>成功率:</label>
          <span>{progressData?.summary?.success_rate?.toFixed(1)}%</span>
        </div>
      </div>

      <div className="steps-container">
        {progressData?.logs?.map(log => (
          <StepExecutionItem
            key={log.id}
            log={log}
            expanded={expandedSteps.has(log.id)}
            onToggleExpand={() => {
              const newExpanded = new Set(expandedSteps);
              if (newExpanded.has(log.id)) {
                newExpanded.delete(log.id);
              } else {
                newExpanded.add(log.id);
              }
              setExpandedSteps(newExpanded);
            }}
            onClick={onStepClick}
          />
        ))}
      </div>
    </div>
  );
};
```

### 步骤执行项组件

```typescript
const StepExecutionItem = ({ log, expanded, onToggleExpand, onClick }) => {
  return (
    <div className="step-execution-item">
      <div className="step-header" onClick={onClick}>
        <StatusIcon status={log.status} />
        <div className="step-info">
          <div className="step-title">
            <span className="step-order">#{log.execution_order}</span>
            <span className="step-name">{log.step_name}</span>
          </div>
          <div className="step-meta">
            <span className="step-type">{log.step_type}</span>
            {log.round_index > 1 && <span className="round-badge">R{log.round_index}</span>}
            {log.loop_iteration > 0 && <span className="loop-badge">L{log.loop_iteration}</span>}
          </div>
        </div>
        <ExpandButton expanded={expanded} onClick={onToggleExpand} />
      </div>

      {expanded && (
        <div className="step-details">
          {/* 基础信息 */}
          <div className="detail-section">
            <h4>执行信息</h4>
            <div className="detail-grid">
              <div className="detail-item">
                <label>状态:</label>
                <StatusBadge status={log.status} />
              </div>
              <div className="detail-item">
                <label>结果类型:</label>
                <span>{log.result_type || 'N/A'}</span>
              </div>
              <div className="detail-item">
                <label>执行时长:</label>
                <span>{formatDuration(log.duration_ms)}</span>
              </div>
              <div className="detail-item">
                <label>内存使用:</label>
                <span>{log.memory_usage_mb?.toFixed(2) || 'N/A'} MB</span>
              </div>
            </div>
          </div>

          {/* 时间信息 */}
          <div className="detail-section">
            <h4>时间信息</h4>
            <div className="detail-grid">
              <div className="detail-item">
                <label>创建时间:</label>
                <span>{formatTime(log.created_at)}</span>
              </div>
              {log.started_at && (
                <div className="detail-item">
                  <label>开始时间:</label>
                  <span>{formatTime(log.started_at)}</span>
                </div>
              )}
              {log.completed_at && (
                <div className="detail-item">
                  <label>完成时间:</label>
                  <span>{formatTime(log.completed_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* 条件和循环信息 */}
          {(log.condition_evaluation !== undefined || log.loop_check_result !== undefined) && (
            <div className="detail-section">
              <h4>条件与循环</h4>
              <div className="detail-grid">
                {log.condition_evaluation !== undefined && (
                  <div className="detail-item">
                    <label>条件评估:</label>
                    <BooleanValue value={log.condition_evaluation} />
                  </div>
                )}
                {log.loop_check_result !== undefined && (
                  <div className="detail-item">
                    <label>循环检查:</label>
                    <BooleanValue value={log.loop_check_result} />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 错误信息 */}
          {log.error_message && (
            <div className="detail-section error">
              <h4>错误信息</h4>
              <div className="error-content">
                {log.error_message}
              </div>
            </div>
          )}

          {/* 结果数据 */}
          {log.result_data && (
            <div className="detail-section">
              <h4>执行结果</h4>
              <div className="result-content">
                <pre>{formatJSON(log.result_data)}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## 🔄 实时更新

### SSE事件处理

```typescript
// SSE事件类型和对应的数据更新
const handleStepProgressEvent = (event: WebSocketMessage) => {
  const { event, data } = event;

  switch (event) {
    case 'step_started':
      // 步骤开始执行
      updateStepStatus(data.step_id, 'running');
      break;

    case 'step_completed':
      // 步骤执行完成
      updateStepStatus(data.step_id, 'completed');
      refreshProgressData();
      break;

    case 'step_failed':
      // 步骤执行失败
      updateStepStatus(data.step_id, 'failed');
      refreshProgressData();
      break;

    case 'loop_iteration':
      // 循环迭代
      updateLoopIteration(data.step_id, data.iteration);
      break;

    case 'condition_evaluation':
      // 条件评估
      updateConditionResult(data.step_id, data.result);
      break;

    case 'session_status_changed':
      // 会话状态变化
      refreshProgressData();
      break;
  }
};
```

### 状态更新逻辑

```typescript
const updateStepStatus = (stepId: number, newStatus: string) => {
  setProgressData(prev => {
    if (!prev) return prev;

    return {
      ...prev,
      logs: prev.logs.map(log =>
        log.step_id === stepId ? { ...log, status: newStatus } : log
      )
    };
  });
};

const refreshProgressData = () => {
  fetchStepProgress(); // 重新获取完整数据
};
```

---

## 🎨 样式系统

### Tailwind CSS类名

```css
/* 主容器 */
.step-progress-display {
  @apply bg-white border border-gray-200 rounded-lg shadow-sm;
}

/* 紧凑模式 */
.step-progress-display.compact {
  @apply p-4;
}

.step-progress-display.compact .progress-header {
  @apply flex items-center justify-between mb-3;
}

.step-progress-display.compact .progress-list {
  @apply space-y-1;
}

.step-progress-display.compact .step-item {
  @apply flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-gray-50 transition-colors;
}

/* 详细模式 */
.step-progress-display.detailed {
  @apply p-6;
}

.step-progress-display.detailed .progress-header {
  @apply flex items-center justify-between mb-4 pb-4 border-b;
}

.step-progress-display.detailed .progress-summary {
  @apply grid grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg;
}

/* 步骤执行项 */
.step-execution-item {
  @apply border border-gray-200 rounded-lg mb-2 overflow-hidden;
}

.step-execution-item .step-header {
  @apply flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors;
}

.step-execution-item .step-details {
  @apply p-4 border-t border-gray-200 bg-gray-50 space-y-4;
}

.step-execution-item .detail-section {
  @apply border border-gray-200 rounded-lg p-4 bg-white;
}

.step-execution-item .detail-section h4 {
  @apply text-sm font-semibold text-gray-700 mb-3;
}

.step-execution-item .detail-grid {
  @apply grid grid-cols-2 gap-3;
}

.step-execution-item .detail-item {
  @apply flex flex-col gap-1;
}

.step-execution-item .detail-item label {
  @apply text-xs font-medium text-gray-500;
}

.step-execution-item .detail-item span {
  @apply text-sm text-gray-900;
}

/* 状态样式 */
.status-pending { @apply text-yellow-600; }
.status-running { @apply text-blue-600 animate-pulse; }
.status-completed { @apply text-green-600; }
.status-failed { @apply text-red-600; }
.status-skipped { @apply text-gray-600; }
.status-timeout { @apply text-orange-600; }

/* 状态徽章 */
.status-badge {
  @apply px-2 py-1 text-xs font-medium rounded-full;
}

.status-badge.pending { @apply bg-yellow-100 text-yellow-800; }
.status-badge.running { @apply bg-blue-100 text-blue-800; }
.status-badge.completed { @apply bg-green-100 text-green-800; }
.status-badge.failed { @apply bg-red-100 text-red-800; }
.status-badge.skipped { @apply bg-gray-100 text-gray-800; }
.status-badge.timeout { @apply bg-orange-100 text-orange-800; }

/* 轮次和迭代徽章 */
.round-badge, .loop-badge {
  @apply px-2 py-1 text-xs font-medium rounded bg-purple-100 text-purple-800;
}
```

---

## 📊 性能优化

### 已实现的优化

1. **智能缓存**:
   ```typescript
   // API响应缓存
   const cacheKey = `step_progress_${sessionId}_page_${page}`;

   // 自动缓存失效
   useEffect(() => {
     return () => {
       cacheService.delete(cacheKey);
     };
   }, [sessionId, page]);
   ```

2. **懒加载详情**:
   ```typescript
   // 仅在需要时获取详细数据
   const includeDetails = expandedSteps.size > 0;

   const response = await fetch(
     `/api/sessions/${sessionId}/step-progress?include_details=${includeDetails}`
   );
   ```

3. **防抖刷新**:
   ```typescript
   // 防抖处理快速连续的刷新请求
   const debouncedRefresh = useMemo(
     () => debounce(fetchStepProgress, 1000),
     [sessionId]
   );
   ```

4. **虚拟滚动** (大数据集):
   ```typescript
   // 当步骤数量超过阈值时启用虚拟滚动
   if (totalSteps > 100) {
     return (
       <VirtualizedList
         height={400}
         itemCount={totalSteps}
         itemSize={80}
         renderItem={renderStepItem}
       />
     );
   }
   ```

---

## 🧪 测试

### 组件单元测试

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { StepProgressDisplay } from './StepProgressDisplay';
import { StepProgressProvider } from '../../contexts/StepProgressContext';

describe('StepProgressDisplay', () => {
  const mockProgressData = {
    logs: [
      {
        id: 1,
        session_id: 1,
        step_id: 1,
        execution_order: 1,
        status: 'completed',
        created_at: '2025-12-05T10:00:00Z',
        started_at: '2025-12-05T10:00:01Z',
        completed_at: '2025-12-05T10:00:05Z',
        duration_ms: 4000,
        step_name: '步骤1'
      }
    ],
    summary: {
      total_steps: 3,
      completed_steps: 1,
      progress_percentage: 33.3
    },
    pagination: {
      page: 1,
      per_page: 50,
      total: 3
    }
  };

  test('renders step progress correctly', () => {
    render(
      <StepProgressDisplay
        sessionId={1}
        compact={false}
        showDetails={false}
      />
    );

    expect(screen.getByText('步骤进度')).toBeInTheDocument();
    expect(screen.getByText('1/3')).toBeInTheDocument();
  });

  test('handles step click events', () => {
    const onStepClick = jest.fn();

    render(
      <StepProgressDisplay
        sessionId={1}
        onStepClick={onStepClick}
      />
    );

    const stepItem = screen.getByText('步骤1');
    fireEvent.click(stepItem);

    expect(onStepClick).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 1,
        step_name: '步骤1',
        status: 'completed'
      })
    );
  });

  test('displays execution details when expanded', async () => {
    render(
      <StepProgressDisplay
        sessionId={1}
        showDetails={true}
      />
    );

    // 测试详情展开
    const expandButton = screen.getByRole('button', { name: /expand/i });
    fireEvent.click(expandButton);

    expect(screen.getByText('执行信息')).toBeInTheDocument();
    expect(screen.getByText('时间信息')).toBeInTheDocument();
  });
});
```

### 集成测试

```typescript
describe('StepProgress Integration', () => {
  test('integrates with real API', async () => {
    const { result } = renderHook(() => useStepProgress({ sessionId: 1 }));

    // 等待数据加载
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.progressData).toBeDefined();
    expect(result.current.progressData.logs).toHaveLength(greaterThan(0));
  });

  test('receives real-time updates', async () => {
    const { result } = renderHook(() => useStepProgress({ sessionId: 1 }));

    // 模拟SSE事件
    act(() => {
      mockWebSocketServer.emit('step_completed', {
        session_id: 1,
        step_id: 2,
        data: { status: 'completed' }
      });
    });

    await waitFor(() => {
      expect(result.current.progressData.logs).toContainEqual(
        expect.objectContaining({
          step_id: 2,
          status: 'completed'
        })
      );
    });
  });
});
```

---

## 🔧 故障排除

### 常见问题

1. **步骤进度不更新**
   - 检查SSE连接状态
   - 验证`autoRefresh`设置
   - 确认sessionId正确

2. **性能问题**
   - 启用缓存: `use_cache=true`
   - 减少刷新频率
   - 使用虚拟滚动

3. **状态显示错误**
   - 检查数据格式
   - 验证状态枚举值
   - 确认时间格式

### 调试技巧

```typescript
// 开发模式调试
const debugMode = process.env.NODE_ENV === 'development';

if (debugMode) {
  console.log('StepProgress Debug:', {
    progressData,
    loading,
    error,
    lastUpdate: new Date().toISOString()
  });
}

// 性能监控
const usePerformanceMonitor = () => {
  const startTime = useRef<number>();

  useEffect(() => {
    startTime.current = performance.now();

    return () => {
      const duration = performance.now() - startTime.current;
      if (duration > 1000) {
        console.warn(`Slow rendering detected: ${duration}ms`);
      }
    };
  });
};
```

---

## 📝 更新日志

### v1.0.0 (2025-12-05) - 基于代码实现的重写

**重大变更**:
- 🔄 **数据结构**: 从步骤列表改为执行日志格式
- 🔄 **API端点**: 统一details端点替代拆分端点
- 🔄 **状态管理**: 使用hooks替代Redux
- ➕ **新特性**: 虚拟滚动、缓存、权限系统

**新增功能**:
- ✅ 虚拟滚动支持大数据集
- ✅ Redis缓存集成
- ✅ 权限控制框架
- ✅ 实时SSE更新
- ✅ 性能监控和统计

### v0.9.0 (原始设计)

**原始设计特点**:
- 步骤列表数据结构
- Redux状态管理
- WebSocket优先
- 拆分API端点

---

**文档最后更新**: 2025-12-05
**基于版本**: 当前代码库实现
**状态**: ✅ 已实现并验证