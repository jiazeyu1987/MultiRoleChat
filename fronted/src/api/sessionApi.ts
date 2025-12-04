import { apiClient } from './roleApi';

// 会话相关的类型定义
export interface SessionRole {
  id: number;
  session_id: number;
  role_id: number;
  role_ref: string;
  assigned_at: string;
}

export interface Session {
  id: number;
  user_id?: number;
  topic: string;
  flow_template_id: number;
  flow_snapshot?: any;
  roles_snapshot?: any;
  status: 'not_started' | 'running' | 'paused' | 'finished' | 'failed' | 'terminated';
  current_step_id?: number;
  current_round: number;
  executed_steps_count: number;
  error_reason?: string;
  created_at: string;
  updated_at: string;
  ended_at?: string;
  session_roles?: SessionRole[];
}

export interface Message {
  id: number;
  session_id: number;
  speaker_session_role_id: number;
  target_session_role_id?: number;
  reply_to_message_id?: number;
  speaker_role_name?: string;
  target_role_name?: string;
  content: string;
  content_summary?: string;
  round_index: number;
  section?: string;
  created_at: string;
}

export interface ExecutionInfo {
  current_step_id?: number;
  next_step_id?: number;
  executed_steps_count: number;
  current_round: number;
  is_finished: boolean;
  termination_reason?: string;
  flow_logic_applied?: {
    next_step_order?: number;
    exit_condition_met?: boolean;
    max_loops_reached?: boolean;
  };
}

export interface CreateSessionRequest {
  topic: string;
  flow_template_id: number;
  role_mappings: Record<string, number>; // {"role_ref": role_id}
  user_id?: number;
}

export interface SessionExecutionRequest {
  // 执行步骤的额外参数，目前为空
  [key: string]: any;
}

export interface SessionListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  user_id?: number;
}

export interface SessionListResult {
  items: Session[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface MessageListParams {
  page?: number;
  page_size?: number;
  round_number?: number;
  role_ref?: string;
  message_type?: string;
}

export interface MessageListResult {
  items: Message[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// 会话API服务
export const sessionApi = {
  /**
   * 获取会话列表
   */
  async getSessions(params?: SessionListParams): Promise<SessionListResult> {
    const queryParams = {
      page: params?.page || 1,
      page_size: params?.page_size || 20,
      search: params?.search,
      status: params?.status,
      user_id: params?.user_id,
    };

    const response = await apiClient.get<{
      sessions: Session[];
      total: number;
      page: number;
      page_size: number;
      pages: number;
    }>('/api/sessions', queryParams);

    return {
      items: response.sessions,
      total: response.total,
      page: response.page,
      page_size: response.page_size,
      pages: response.pages,
    };
  },

  /**
   * 获取会话详情
   */
  async getSession(id: number): Promise<Session> {
    return apiClient.get<Session>(`/api/sessions/${id}`);
  },

  /**
   * 创建新会话
   */
  async createSession(sessionData: CreateSessionRequest): Promise<Session> {
    return apiClient.post<Session>('/api/sessions', sessionData);
  },

  /**
   * 更新会话
   */
  async updateSession(id: number, sessionData: Partial<CreateSessionRequest>): Promise<Session> {
    return apiClient.put<Session>(`/api/sessions/${id}`, sessionData);
  },

  /**
   * 删除会话
   */
  async deleteSession(id: number): Promise<void> {
    return apiClient.delete<void>(`/api/sessions/${id}`);
  },

  /**
   * 执行会话的下一步骤
   */
  async executeNextStep(sessionId: number, executionData?: SessionExecutionRequest): Promise<{
    message: Message;
    execution_info: ExecutionInfo;
  }> {
    return apiClient.post<{
      message: Message;
      execution_info: ExecutionInfo;
    }>(`/api/sessions/${sessionId}/run-next-step`, executionData || {});
  },

  /**
   * 暂停会话
   */
  async pauseSession(sessionId: number): Promise<Session> {
    return apiClient.post<Session>(`/api/sessions/${sessionId}/pause`);
  },

  /**
   * 恢复会话
   */
  async resumeSession(sessionId: number): Promise<Session> {
    return apiClient.post<Session>(`/api/sessions/${sessionId}/resume`);
  },

  /**
   * 终止会话
   */
  async terminateSession(sessionId: number): Promise<Session> {
    return apiClient.post<Session>(`/api/sessions/${sessionId}/terminate`);
  },

  /**
   * 获取会话的消息列表
   */
  async getMessages(sessionId: number, params?: MessageListParams): Promise<MessageListResult> {
    const queryParams = {
      page: params?.page || 1,
      page_size: params?.page_size || 50,
      round_number: params?.round_number,
      role_ref: params?.role_ref,
      message_type: params?.message_type,
    };

    const response = await apiClient.get<{
      messages: Message[];
      total: number;
      page: number;
      page_size: number;
      pages: number;
    }>(`/api/sessions/${sessionId}/messages`, queryParams);

    return {
      items: response.messages,
      total: response.total,
      page: response.page,
      page_size: response.page_size,
      pages: response.pages,
    };
  },

  /**
   * 获取单条消息详情
   */
  async getMessage(sessionId: number, messageId: number): Promise<Message> {
    return apiClient.get<Message>(`/api/sessions/${sessionId}/messages/${messageId}`);
  },

  /**
   * 获取会话的流程进度信息
   */
  async getSessionFlow(sessionId: number): Promise<{
    current_step: any;
    executed_steps: any[];
    remaining_steps: any[];
    total_steps: number;
    progress_percentage: number;
  }> {
    return apiClient.get<any>(`/api/sessions/${sessionId}/flow`);
  },

  /**
   * 导出会话记录
   */
  async exportSession(sessionId: number, format: 'json' | 'csv' | 'txt' = 'json'): Promise<any> {
    return apiClient.get<any>(`/api/sessions/${sessionId}/export?format=${format}`);
  },

  /**
   * 获取会话统计信息
   */
  async getSessionStatistics(sessionId: number): Promise<{
    total_messages: number;
    messages_by_type: Record<string, number>;
    messages_by_role: Record<string, number>;
    average_response_time: number;
    total_execution_time: number;
    rounds_completed: number;
  }> {
    return apiClient.get<any>(`/api/sessions/${sessionId}/messages/statistics`);
  },
};