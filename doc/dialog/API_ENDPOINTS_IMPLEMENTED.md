# API 端点实现文档

## 📡 基于代码实现的API端点说明

> **注意**: 本文档基于当前代码实现，与原始设计文档存在差异。请以此为准。

---

## 🔍 核心差异说明

### 数据结构变化
- **步骤进度**: 从步骤列表改为执行日志格式
- **LLM交互**: 从嵌套input/output改为平铺字段
- **查询参数**: 从limit/offset改为page/per_page分页

### 端点整合
- `GET /api/sessions/{id}/steps/{step_id}` → `GET /api/step-execution/{log_id}/details`
- `GET /api/sessions/{id}/llm-interactions/{id}/input` + `.../output` → `GET /api/llm-interactions/{id}/details`

---

## 📋 实际API端点列表

### 1. 会话管理

#### 获取会话列表
```http
GET /api/sessions
Query Parameters:
- page: 页码 (默认: 1)
- page_size: 每页数量 (默认: 20)
- status: 状态过滤 (可选)
- flow_template_id: 流程模板ID过滤 (可选)
```

**响应格式**:
```json
{
  "sessions": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 50,
    "pages": 3,
    "has_prev": false,
    "has_next": true
  }
}
```

#### 创建会话
```http
POST /api/sessions
Content-Type: application/json

{
  "topic": "会话主题",
  "flow_template_id": 1,
  "roles_snapshot": "[]",  // 可选
  "flow_snapshot": "{}"     // 可选
}
```

#### 获取会话详情
```http
GET /api/sessions/{session_id}
```

#### 执行下一步
```http
POST /api/sessions/{session_id}/run-next-step
```

---

### 2. 步骤进度 ⭐ **重要差异**

#### 获取步骤进度 - **执行日志格式**
```http
GET /api/sessions/{session_id}/step-progress
Query Parameters:
- page: 页码 (默认: 1)
- per_page: 每页数量 (默认: 50)
- include_details: 是否包含详细信息 (默认: false)
- use_cache: 是否使用缓存 (默认: true)
```

**响应格式**:
```json
{
  "logs": [
    {
      "id": 1,
      "session_id": 1,
      "step_id": 1,
      "execution_order": 1,
      "round_index": 1,
      "loop_iteration": 0,
      "attempt_count": 1,
      "status": "completed",
      "result_type": "success",
      "duration_ms": 1500,
      "created_at": "2025-12-05T10:00:00Z",
      "started_at": "2025-12-05T10:00:00Z",
      "completed_at": "2025-12-05T10:00:02Z",
      "step_snapshot": "{...}",
      "context_snapshot": "{...}"
    }
  ],
  "summary": {
    "total_steps": 3,
    "completed_steps": 2,
    "failed_steps": 0,
    "running_steps": 1,
    "progress_percentage": 66.7,
    "current_step": {
      "id": 3,
      "name": "步骤3",
      "status": "running"
    }
  },
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 3,
    "pages": 1,
    "has_prev": false,
    "has_next": false
  }
}
```

#### 获取流程可视化 - **非图结构**
```http
GET /api/sessions/{session_id}/flow-visualization
Query Parameters:
- use_cache: 是否使用缓存 (默认: true)
```

**响应格式**:
```json
{
  "session_id": 1,
  "flow_template_id": 1,
  "current_step_id": 3,
  "session_status": "running",
  "total_steps": 3,
  "completed_steps": 2,
  "steps": [
    {
      "id": 1,
      "name": "步骤1",
      "step_type": "dialogue",
      "description": "描述",
      "order": 1,
      "executions": [
        {
          "log_id": 1,
          "status": "completed",
          "result_type": "success",
          "round_index": 1,
          "duration_ms": 1500
        }
      ]
    }
  ]
}
```

#### 获取步骤执行详情 - **按日志ID**
```http
GET /api/step-execution/{log_id}/details
```

**响应格式**:
```json
{
  "id": 1,
  "session_id": 1,
  "step_id": 1,
  "execution_order": 1,
  "status": "completed",
  "result_type": "success",
  "result_data": "{...}",
  "condition_evaluation": true,
  "duration_ms": 1500,
  "memory_usage_mb": 45.2,
  "step_snapshot": "{...}",
  "context_snapshot": "{...}"
}
```

---

### 3. LLM交互 ⭐ **重要差异**

#### 获取LLM交互记录 - **平铺字段结构**
```http
GET /api/sessions/{session_id}/llm-interactions
Query Parameters:
- page: 页码 (默认: 1)
- per_page: 每页数量 (默认: 50)
- include_details: 是否包含详细信息 (默认: false)
- status: 状态过滤 (可选)
```

**响应格式**:
```json
{
  "interactions": [
    {
      "id": 1,
      "session_id": 1,
      "step_id": 1,
      "session_role_id": 1,
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "request_id": "req_123456",
      "system_prompt": "系统提示词...",
      "user_prompt": "用户提示词...",
      "full_prompt": "完整提示词...",
      "response_content": "响应内容...",
      "raw_response": "{...}",
      "status": "completed",  // pending/streaming/completed/failed/timeout
      "usage_input_tokens": 150,
      "usage_output_tokens": 200,
      "usage_total_tokens": 350,
      "latency_ms": 2500,
      "created_at": "2025-12-05T10:00:00Z",
      "started_at": "2025-12-05T10:00:00Z",
      "completed_at": "2025-12-05T10:00:03Z",
      "step_info": {
        "id": 1,
        "name": "步骤1",
        "type": "dialogue"
      },
      "role_info": {
        "id": 1,
        "name": "教师",
        "role_ref": "teacher"
      }
    }
  ],
  "statistics": {
    "total_interactions": 10,
    "completed_interactions": 8,
    "failed_interactions": 1,
    "active_interactions": 1,
    "success_rate": 80.0,
    "total_input_tokens": 1500,
    "total_output_tokens": 2000,
    "total_tokens": 3500,
    "average_latency_ms": 2000
  },
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 10,
    "pages": 1,
    "has_prev": false,
    "has_next": false
  }
}
```

#### 获取LLM交互详情 - **统一端点**
```http
GET /api/llm-interactions/{interaction_id}/details
```

**响应格式**: 完整的交互对象，包含所有字段

#### 获取LLM统计
```http
GET /api/sessions/{session_id}/llm-statistics
Query Parameters:
- days: 统计天数 (默认: 7)
```

---

### 4. 实时更新 ⭐ **SSE优先**

#### 会话实时更新
```http
GET /api/sessions/{session_id}/live
Accept: text/event-stream
```

**事件格式**:
```javascript
{
  "event": "connected",
  "session_id": 1,
  "data": {
    "message": "Connected to session live updates"
  },
  "timestamp": "2025-12-05T10:00:00Z"
}

// 当前实际支持的SSE事件类型:
- connected              // 连接建立
- initial_status         // 初始状态快照
- heartbeat              // 定时心跳（每5秒）

// 注意：当前实现主要依赖轮询获取数据更新
// SSE仅提供连接状态和心跳，实际的step/LLM事件通过定时轮询获取
```

#### 系统实时更新
```http
GET /api/system/live
Accept: text/event-stream
```

---

### 5. 基础数据管理

#### 角色管理
```http
GET    /api/roles
POST   /api/roles
GET    /api/roles/{id}
PUT    /api/roles/{id}
DELETE /api/roles/{id}
```

#### 流程模板管理
```http
GET    /api/flows
POST   /api/flows
GET    /api/flows/{id}
PUT    /api/flows/{id}
DELETE /api/flows/{id}
```

#### 消息管理
```http
GET    /api/sessions/{session_id}/messages
GET    /api/sessions/{session_id}/messages/{message_id}
PUT    /api/sessions/{session_id}/messages/{message_id}
DELETE /api/sessions/{session_id}/messages/{message_id}
```

**获取消息列表**
```http
GET /api/sessions/{session_id}/messages
Query Parameters:
- page: 页码 (默认: 1)
- page_size: 每页数量 (默认: 20)
- include_session_roles: 是否包含会话角色信息 (默认: false)
```

**获取消息详情**
```http
GET /api/sessions/{session_id}/messages/{message_id}
```

**更新消息**
```http
PUT /api/sessions/{session_id}/messages/{message_id}
Content-Type: application/json

{
  "content": "更新的消息内容"
}
```

**删除消息**
```http
DELETE /api/sessions/{session_id}/messages/{message_id}
```

---

### 6. 系统监控

#### 健康检查
```http
GET /api/health
```

#### 系统指标
```http
GET /api/monitoring/metrics
```

#### LLM系统指标
```http
GET /api/llm-interactions/metrics
```

---

## 🔧 实现特性

### 1. 缓存策略
- Redis缓存支持
- 自动缓存失效
- 可配置TTL

### 2. 安全机制
- 数据安全过滤
- 敏感信息屏蔽
- 输入验证和清理

### 3. 性能优化
- 数据库索引
- 分页查询
- 虚拟滚动支持

### 4. 错误处理
- 统一错误格式
- 详细错误日志
- 优雅降级

---

## 📝 使用示例

### JavaScript/TypeScript
```typescript
// 获取步骤进度
const response = await fetch(`/api/sessions/${sessionId}/step-progress?page=1&per_page=20`);
const data = await response.json();

// 监听实时更新
const eventSource = new EventSource(`/api/sessions/${sessionId}/live`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('实时事件:', data.event, data.data);
};
```

### Python
```python
import requests

# 获取LLM交互记录
response = requests.get(
    f'/api/sessions/{session_id}/llm-interactions',
    params={'page': 1, 'per_page': 20, 'status': 'completed'}
)
data = response.json()
```

---

## 🚨 注意事项

1. **权限控制**: 当前实现中权限系统框架存在但未完全集成
2. **用户系统**: 用户ID字段预留但未实现完整用户管理
3. **WebSocket**: 主要使用SSE，WebSocket服务预留
4. **字段命名**: 使用snake_case命名，前端转换为camelCase

---

**最后更新**: 2025-12-05
**基于版本**: 当前代码库实现