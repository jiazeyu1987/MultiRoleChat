# 前端组件实现文档

## 🎨 基于代码实现的组件说明

> **注意**: 本文档基于当前代码实现，与原始设计文档存在差异。请以此为准。

---

## 🔍 核心架构差异

### 组件组织
- **文档规划**: `components/session/*` + Redux store
- **实际实现**: `components/*.tsx` + hooks，无Redux

### 状态管理
- **文档规划**: Redux状态管理
- **实际实现**: React hooks + local state + 自定义hooks

### 实时通信
- **文档规划**: WebSocket + 自定义事件类型
- **实际实现**: SSE优先 + 统一事件格式

---

## 📦 实际组件清单

### 1. StepProgressDisplay.tsx ⭐ **重要差异**

#### 实际Props
```typescript
interface StepProgressDisplayProps {
  sessionId: number;
  compact?: boolean;           // 紧凑模式 vs 详细模式
  showDetails?: boolean;       // 是否显示详情
  autoRefresh?: boolean;       // 自动刷新
  refreshInterval?: number;    // 刷新间隔(ms)
  onStepClick?: (step: StepInfo) => void; // 点击回调
}
```

#### 实际数据结构
```typescript
interface StepInfo {
  id: number;
  name: string;
  step_type: string;         // dialogue/condition/loop/end
  description: string;
  order: number;
  executions: Array<{        // 执行历史，不是当前状态
    log_id: number;
    status: string;           // pending/running/completed/failed
    result_type: string;
    round_index: number;
    loop_iteration: number;
    duration_ms: number;
    error_message?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
  }>;
}
```

#### 使用方式差异
```typescript
// 文档规划 (未实现)
<StepProgressDisplay
  sessionId={id}
  steps={currentStepData}     // 不存在
  onStepClick={handleStepClick}
/>

// 实际实现
<StepProgressDisplay
  sessionId={id}
  compact={true}
  showDetails={false}
  autoRefresh={true}
  onStepClick={(step) => console.log(step)} // 传入完整StepInfo对象
/>
```

---

### 2. LLMIODisplay.tsx ⭐ **重要差异**

#### 实际Props
```typescript
interface LLMIODisplayProps {
  sessionId: number;
  compact?: boolean;                    // 紧凑模式
  showDetails?: boolean;                // 显示详细信息
  autoRefresh?: boolean;                // 自动刷新
  refreshInterval?: number;             // 刷新间隔
  maxItems?: number;                    // 最大项目数
  showStreaming?: boolean;              // 显示流式内容
  showDebugInfo?: boolean;              // 显示调试信息
  enableVirtualScrolling?: boolean;     // 启用虚拟滚动
  virtualScrollThreshold?: number;      // 虚拟滚动阈值
  virtualItemHeight?: number;           // 虚拟项目高度
}
```

#### 实际数据结构 (平铺字段)
```typescript
interface LLMInteraction {
  id: number;
  session_id: number;
  step_id?: number;
  session_role_id?: number;
  provider: string;
  model?: string;
  request_id?: string;

  // 平铺的输入输出字段 (非嵌套)
  system_prompt?: string;
  user_prompt: string;
  full_prompt?: any;
  response_content?: string;
  raw_response?: any;

  status: 'pending' | 'streaming' | 'completed' | 'failed' | 'timeout';
  error_message?: string;
  latency_ms?: number;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };

  created_at: string;
  started_at?: string;
  completed_at?: string;

  step_info?: { id: number; name: string; type: string; };
  role_info?: { id: number; name: string; role_ref: string; };
}
```

#### 虚拟滚动实现
```typescript
// 自动启用条件
const shouldUseVirtualScrolling = enableVirtualScrolling &&
                                 filteredInteractions.length > virtualScrollThreshold;

// 虚拟滚动组件
<List
  height={384}
  itemCount={filteredInteractions.length}
  itemSize={getItemHeight}
  itemData={filteredInteractions}
  overscanCount={5}
>
  {VirtualInteractionRow}
</List>
```

---

### 3. EnhancedSessionTheater.tsx

#### 核心集成
```typescript
interface EnhancedSessionTheaterProps {
  sessionId: number;
  onExit: () => void;
  theme?: any;
  enableDebugPanel?: boolean;     // 调试面板
  enableStepProgress?: boolean;   // 步骤进度
  enableLLMDebug?: boolean;       // LLM调试
  autoRefresh?: boolean;          // 自动刷新
  compactMode?: boolean;          // 紧凑模式
}
```

#### 标签页结构
```typescript
const [activeTab, setActiveTab] = useState<
  'theater' | 'progress' | 'llm' | 'visualization'
>('theater');

// 标签页内容
{activeTab === 'progress' && (
  <StepProgressDisplay sessionId={sessionId} />
)}

{activeTab === 'llm' && (
  <LLMIODisplay sessionId={sessionId} />
)}
```

---

## 🔧 自定义Hooks实现

### 1. useStepProgress.ts

#### 实际签名
```typescript
interface UseStepProgressOptions {
  sessionId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  includeDetails?: boolean;
  page?: number;                  // 分页参数
  perPage?: number;               // 每页数量
  enableRealtime?: boolean;       // 启用实时更新
}

interface UseStepProgressReturn {
  flowData: {
    session_id: number;
    flow_template_id: number;
    current_step_id?: number;
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
        duration_ms?: number;
      }>;
    }>;
  };
  progressData: {
    logs: Array<{
      id: number;
      session_id: number;
      step_id: number;
      execution_order: number;
      round_index: number;
      loop_iteration: number;
      attempt_count: number;
      status: string;
      result_type: string;
      duration_ms?: number;
      created_at: string;
      started_at?: string;
      completed_at?: string;
    }>;
    summary: {
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
    };
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
      has_prev: boolean;
      has_next: boolean;
    };
  };
  loading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;
  hasMore: boolean;

  // 分页控制
  refetch: () => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  loadPage: (page: number) => void;
  loadMore: () => void;

  // 实时更新控制
  enableRealtime: boolean;
  toggleRealtime: () => void;
  refreshInterval: number;
  toggleAutoRefresh: () => void;

  // 数据处理
  exportData: (format: 'json' | 'csv') => string;
  getExecutionDetails: (logId: number) => Promise<any>;
}
```

#### 使用方式
```typescript
const {
  flowData,
  progressData,
  loading,
  error,
  refetch
} = useStepProgress({
  sessionId,
  autoRefresh: true,
  includeDetails: true
});
```

#### 内部实现差异
- 同时调用 `/step-progress` 和 `/flow-visualization` 端点
- 集成SSE实时更新
- 自动缓存和错误处理
- 支持分页和过滤

---

### 2. useLLMInteractions.ts

#### 实际签名
```typescript
interface UseLLMInteractionsOptions {
  sessionId: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  includeDetails?: boolean;
  page?: number;
  perPage?: number;
  statusFilter?: 'all' | 'pending' | 'streaming' | 'completed' | 'failed' | 'timeout';
}

interface UseLLMInteractionsReturn {
  interactions: LLMInteraction[];
  statistics: {
    total_interactions: number;
    completed_interactions: number;
    failed_interactions: number;
    success_rate: number;
    total_input_tokens: number;
    total_output_tokens: number;
    average_latency_ms: number;
    cost_estimate_usd?: number;
  };
  loading: boolean;
  error: string | null;
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
    has_prev: boolean;
    has_next: boolean;
  };
  currentFilter: string;
  hasMore: boolean;

  // 分页控制方法
  refetch: () => void;
  setPage: (page: number) => void;
  loadPage: (page: number) => void;
  loadMore: () => void;

  // 筛选控制方法
  setFilter: (statusFilter: string) => void;
  clearFilter: () => void;

  // 数据导出方法
  exportData: (format: 'json' | 'csv') => string;

  // 流式内容获取
  getStreamingContent: (interactionId: number) => string | null;

  // 性能控制
  setPageSize: (size: number) => void;
  toggleAutoRefresh: () => void;
}
```

---

### 3. useWebSocket.ts

#### 实际实现
```typescript
// 支持SSE和WebSocket，优先SSE
const {
  connected,
  error,
  lastMessage,
  connect,
  disconnect
} = useSessionWebSocket(sessionId, {
  autoConnect: true,
  enableLogging: true,
  preferSSE: true  // 默认优先使用SSE
});
```

#### 事件处理
```typescript
// 统一事件格式
interface WebSocketMessage {
  event: string;
  session_id: number;
  data: any;
  timestamp: string;
}

// 当前实际SSE事件类型
- connected              // 连接建立
- initial_status         // 初始状态快照
- heartbeat              // 定时心跳（每5秒）

// 注意：step/LLM相关事件通过轮询获取，SSE仅提供连接状态
```

---

## 🗂️ 目录结构

### 实际文件组织
```
fronted/src/
├── components/
│   ├── StepProgressDisplay.tsx      # ✅ 已实现
│   ├── LLMIODisplay.tsx             # ✅ 已实现
│   ├── StepVisualization.tsx        # ✅ 已实现
│   ├── DebugPanel.tsx               # ✅ 已实现
│   └── EnhancedSessionTheater.tsx   # ✅ 已实现
├── hooks/
│   ├── useStepProgress.ts           # ✅ 已实现
│   ├── useLLMInteractions.ts        # ✅ 已实现
│   ├── useWebSocket.ts              # ✅ 已实现
│   ├── usePermissions.ts            # ✅ 已实现
│   ├── usePerformanceOptimizations.ts # ✅ 已实现
│   └── useUserPreferences.ts        # ✅ 已实现
├── api/
│   └── sessionApi.ts                # ✅ 已实现 (简化版)
└── utils/
    └── errorHandler.ts              # ✅ 已实现
```

### 未实现的结构
```
components/session/*    # ❌ 不存在
store/                   # ❌ 不存在 (使用hooks替代)
services/*              # ❌ 不存在 (hooks中直接fetch)
```

---

## 🎨 样式和主题

### Tailwind CSS类名约定
- `step-progress-display` - 主容器
- `llm-io-display` - LLM显示主容器
- `debug-panel` - 调试面板主容器
- `enhanced-session-theater` - 会话剧场主容器

### 主题变量
```typescript
const theme = {
  bgSoft: 'bg-blue-100',
  text: 'text-blue-600',
  primary: '#3B82F6',
  // 可通过props传入自定义主题
};
```

---

## 🔌 API集成示例

### 步骤进度数据获取
```typescript
// useStepProgress内部实现
const fetchStepProgress = async () => {
  const response = await fetch(
    `/api/sessions/${sessionId}/step-progress?page=${page}&per_page=${perPage}&include_details=${includeDetails}`
  );
  const result = await response.json();
  return result.data; // { logs, summary, current_step, pagination }
};
```

### LLM交互数据获取
```typescript
// useLLMInteractions内部实现
const fetchLLMInteractions = async () => {
  const response = await fetch(
    `/api/sessions/${sessionId}/llm-interactions?page=${page}&per_page=${perPage}&include_details=${includeDetails}&status=${statusFilter}`
  );
  const result = await response.json();
  return result.data; // { interactions, statistics, pagination, currentFilter, hasMore }
};
```

### 实时更新
```typescript
// useWebSocket内部实现
const setupSSEConnection = () => {
  const eventSource = new EventSource(`/api/sessions/${sessionId}/live`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleRealtimeEvent(data);
  };
};
```

---

## 📊 性能优化特性

### 1. 虚拟滚动
- 自动启用阈值: 100个项目
- 动态项目高度
- Intersection Observer优化渲染

### 2. 缓存策略
- API响应缓存
- 去重请求
- 内存使用监控

### 3. 懒加载
- 组件按需加载
- 详情数据延迟获取
- 图片和资源优化

---

## 🚨 重要说明

### 1. Props命名差异
- `maxMessages` → `maxItems`
- `showTimestamp` → 集成在数据中
- `enableSyntaxHighlight` → 默认启用

### 2. 状态管理差异
- 无Redux store
- 使用React hooks + context
- 本地状态优先

### 3. 实时通信差异
- SSE优先，WebSocket兼容
- 统一事件格式
- 自动重连机制

---

**最后更新**: 2025-12-05
**基于版本**: 当前代码库实现