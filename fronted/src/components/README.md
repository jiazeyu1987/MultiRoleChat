# Advanced Dialog System Components

这是基于 `doc/dialog` 文档实现的高级对话系统组件，提供实时监控、调试和可视化功能。

## 🎯 功能概述

### 核心组件

#### 1. StepProgressDisplay - 步骤进度显示
- **功能**: 实时显示会话执行进度和步骤状态
- **特性**:
  - 可视化步骤执行流程
  - 进度条和状态指示器
  - 交互式步骤点击查看详情
  - 支持循环和条件可视化
  - 性能指标显示
  - 紧凑和详细视图模式

#### 2. LLMIODisplay - LLM输入输出显示
- **功能**: 实时显示LLM调用记录和调试信息
- **特性**:
  - 实时流式输出显示
  - 完整提示词构建过程可视化
  - 语法高亮（JSON、Markdown、代码）
  - 调试功能（复制、时间戳、性能指标）
  - WebSocket实时更新
  - 过滤和搜索功能

#### 3. StepVisualization - 步骤可视化
- **功能**: 多视图展示步骤执行流程
- **特性**:
  - 流程图视图（SVG）
  - 时间线视图
  - 树形结构视图
  - 交互式节点和连接
  - 性能统计展示

#### 4. DebugPanel - 调试面板
- **功能**: 综合调试和监控工具
- **特性**:
  - 实时事件日志
  - 系统性能指标
  - LLM调用统计
  - 数据库查询监控
  - 导出和分析功能

#### 5. EnhancedSessionTheater - 增强版会话剧场
- **功能**: 集成所有调试和监控功能的增强版会话界面
- **特性**:
  - 多标签页界面
  - 实时WebSocket连接
  - 可折叠面板
  - 权限控制
  - 主题支持

## 🔧 自定义Hooks

### 数据管理Hooks

#### useStepProgress
```typescript
const {
  flowData,
  progressData,
  loading,
  error,
  refetch
} = useStepProgress({
  sessionId: 1,
  autoRefresh: true,
  includeDetails: true
});
```

#### useLLMInteractions
```typescript
const {
  interactions,
  statistics,
  loading,
  error,
  refetch
} = useLLMInteractions({
  sessionId: 1,
  autoRefresh: true,
  includeDetails: true
});
```

#### useWebSocket
```typescript
const {
  connected,
  error,
  lastMessage,
  connect,
  disconnect
} = useSessionWebSocket(sessionId, {
  autoConnect: true,
  enableLogging: true
});
```

### 系统Hooks

#### usePermissions
```typescript
const {
  permissions,
  hasPermission,
  canAccessDebugPanel,
  canViewLLMDetails
} = usePermissions({
  userId: 'user123',
  roles: ['developer']
});
```

#### usePerformanceOptimizations
```typescript
const {
  cache,
  deduplicateRequest,
  createDebouncedFn
} = usePerformanceOptimizations({
  enableVirtualScrolling: true,
  enableItemCaching: true
});
```

#### useUserPreferences
```typescript
const {
  preferences,
  updatePreference,
  updatePreferences
} = useUserPreferences({
  userId: 'user123',
  enablePersistence: true
});
```

## 🚀 快速开始

### 1. 基本使用

```tsx
import React from 'react';
import { StepProgressDisplay } from './components/StepProgressDisplay';

function MyComponent({ sessionId }: { sessionId: number }) {
  return (
    <StepProgressDisplay
      sessionId={sessionId}
      compact={false}
      showDetails={true}
      autoRefresh={true}
    />
  );
}
```

### 2. 完整集成

```tsx
import React from 'react';
import EnhancedSessionTheater from './components/EnhancedSessionTheater';
import { PreferencesProvider } from './hooks/useUserPreferences';

function App() {
  return (
    <PreferencesProvider userId="user123">
      <EnhancedSessionTheater
        sessionId={1}
        onExit={() => console.log('exit')}
        enableDebugPanel={true}
        enableStepProgress={true}
        enableLLMDebug={true}
      />
    </PreferencesProvider>
  );
}
```

### 3. 权限控制

```tsx
import { PermissionGate } from './hooks/usePermissions';

function DebugComponent() {
  return (
    <PermissionGate permission="debug:view" fallback={<div>Access Denied</div>}>
      <DebugPanel sessionId={1} visible={true} onClose={() => {}} />
    </PermissionGate>
  );
}
```

## 📊 API集成

### 后端API端点

#### 步骤进度API
- `GET /api/sessions/{id}/step-progress` - 获取步骤进度
- `GET /api/sessions/{id}/flow-visualization` - 获取流程可视化数据
- `GET /api/sessions/{id}/execution-statistics` - 获取执行统计

#### LLM交互API
- `GET /api/sessions/{id}/llm-interactions` - 获取LLM交互记录
- `GET /api/sessions/{id}/llm-statistics` - 获取LLM统计
- `GET /api/llm-interactions/metrics` - 获取系统LLM指标

#### 实时通信API
- `GET /api/sessions/{id}/live` - Server-Sent Events实时更新
- `GET /api/system/live` - 系统级实时更新
- `POST /api/realtime/test` - 测试实时事件

## 🎨 主题和样式

### CSS类名约定
- `step-progress-display` - 主容器
- `llm-io-display` - LLM显示主容器
- `debug-panel` - 调试面板主容器
- `step-visualization` - 步骤可视化主容器

### 主题变量
组件支持通过props传入主题配置：

```tsx
const theme = {
  bgSoft: 'bg-blue-100',
  text: 'text-blue-600',
  primary: '#3B82F6',
  // ... 其他主题配置
};
```

## 🔧 配置选项

### StepProgressDisplay Props
```typescript
interface StepProgressDisplayProps {
  sessionId: number;
  compact?: boolean;
  showDetails?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onStepClick?: (step: StepInfo) => void;
}
```

### LLMIODisplay Props
```typescript
interface LLMIODisplayProps {
  sessionId: number;
  compact?: boolean;
  showDetails?: boolean;
  autoRefresh?: boolean;
  maxItems?: number;
  showStreaming?: boolean;
  showDebugInfo?: boolean;
}
```

### DebugPanel Props
```typescript
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
```

## 🧪 测试

运行测试套件：

```bash
# 运行集成测试
npm test

# 运行测试覆盖率
npm run test:coverage
```

## 📈 性能优化

### 虚拟滚动
- 大列表自动启用虚拟滚动
- 可配置项目高度和阈值

### 缓存策略
- 智能缓存API响应
- 自动过期和清理
- 内存使用监控

### 请求去重
- 防止重复API调用
- 智能请求合并

## 🔒 安全和权限

### 权限系统
- 基于角色的访问控制
- 细粒度权限管理
- 权限继承和组合

### 数据安全
- 敏感信息过滤
- 匿名化处理
- 安全的导出功能

## 🐛 故障排除

### 常见问题

1. **WebSocket连接失败**
   - 检查后端服务是否运行
   - 验证网络连接
   - 检查防火墙设置

2. **实时更新不工作**
   - 确认SSE端点可用
   - 检查浏览器兼容性
   - 验证事件监听器

3. **性能问题**
   - 启用虚拟滚动
   - 减少自动刷新频率
   - 检查内存使用

### 调试模式

```tsx
// 启用详细日志
const config = {
  enableLogging: true,
  enableDebugPanel: true,
  showAdvancedDebug: true
};
```

## 📝 更新日志

### v1.0.0
- 初始版本发布
- 完整的步骤进度显示
- LLM输入输出调试
- 实时WebSocket通信
- 权限控制系统
- 性能优化功能

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发环境设置
```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

### 代码规范
- 使用TypeScript严格模式
- 遵循ESLint规则
- 添加适当的注释和文档

## 📄 许可证

MIT License