import { apiClient } from './roleApi';

// 流程模板相关的类型定义
export interface FlowStep {
  id: number;
  flow_template_id: number;
  order: number;
  speaker_role_ref: string;
  target_role_ref?: string;
  task_type: 'ask_question' | 'answer_question' | 'review_answer' | 'question' | 'summarize' |
           'evaluate' | 'suggest' | 'challenge' | 'support' | 'conclude';
  context_scope: string | string[];  // 支持字符串和数组格式
  context_param?: Record<string, any>;
  logic_config?: Record<string, any>;  // 统一的字段名
  next_step_id?: number;
  description?: string;
}

export interface FlowTemplate {
  id: number;
  name: string;
  topic?: string;  // 新增的topic字段
  type: 'teaching' | 'review' | 'debate' | 'discussion' | 'interview' | 'other';
  description?: string;
  version?: string;
  is_active: boolean;
  termination_config?: Record<string, any>;
  created_at: string;
  updated_at: string;
  step_count?: number;
  steps?: FlowStep[];
}

export interface FlowTemplateRequest {
  name: string;
  topic?: string;
  type: 'teaching' | 'review' | 'debate' | 'discussion' | 'interview' | 'other';
  description?: string;
  version?: string;
  is_active?: boolean;
  termination_config?: Record<string, any>;
  steps?: Omit<FlowStep, 'id' | 'flow_template_id'>[];
}

export interface FlowListParams {
  page?: number;
  page_size?: number;
  search?: string;
  template_type?: string;
  is_active?: boolean;
}

export interface FlowListResult {
  items: FlowTemplate[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// 内部API响应类型
interface FlowListResponse {
  flows: FlowTemplate[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// 流程模板API服务
export const flowApi = {
  /**
   * 获取流程模板列表
   */
  async getFlows(params?: FlowListParams): Promise<FlowListResult> {
    const queryParams = {
      search: params?.search,
      page: params?.page || 1,
      page_size: params?.page_size || 20,
      // 后端使用的是 type 参数，这里做字段映射
      type: params?.template_type,
      is_active: params?.is_active,
    };

    const response = await apiClient.get<FlowListResponse>('/api/flows', queryParams);

    return {
      items: response.flows,
      total: response.total,
      page: response.page,
      page_size: response.page_size,
      pages: Math.ceil(response.total / response.page_size),
    };
  },

  /**
   * 获取流程模板详情
   */
  async getFlow(id: number): Promise<FlowTemplate> {
    return apiClient.get<FlowTemplate>(`/api/flows/${id}`);
  },

  /**
   * 创建新的流程模板
   */
  async createFlow(flowData: FlowTemplateRequest): Promise<FlowTemplate> {
    return apiClient.post<FlowTemplate>('/api/flows', flowData);
  },

  /**
   * 更新流程模板
   */
  async updateFlow(id: number, flowData: Partial<FlowTemplateRequest>): Promise<FlowTemplate> {
    return apiClient.put<FlowTemplate>(`/api/flows/${id}`, flowData);
  },

  /**
   * 删除流程模板
   */
  async deleteFlow(id: number, softDelete: boolean = true): Promise<void> {
    const endpoint = softDelete
      ? `/api/flows/${id}?soft_delete=true`
      : `/api/flows/${id}`;
    return apiClient.delete<void>(endpoint);
  },

  /**
   * 复制流程模板
   */
  async duplicateFlow(id: number, newName: string, description?: string): Promise<FlowTemplate> {
    // 后端对应路由为 /api/flows/<id>/copy
    return apiClient.post<FlowTemplate>(`/api/flows/${id}/copy`, {
      name: newName,
      description: description,
    });
  },

  /**
   * 获取流程模板统计信息
   */
  async getFlowStatistics(): Promise<{
    total_templates: number;
    active_templates: number;
    inactive_templates: number;
    type_distribution: Record<string, number>;
  }> {
    return apiClient.get<any>('/api/flows/statistics');
  },

  /**
   * 删除所有流程模板
   */
  async clearAllFlows(): Promise<{
    deleted_templates: number;
    deleted_steps: number;
  }> {
    return apiClient.delete<any>('/api/flows/clear-all');
  },
};
