import {
  Role,
  RoleRequest,
  RoleListParams,
  RoleListResult,
  RoleListResponse,
  ApiResponse,
  ApiError
} from '../types/role';

// API基础URL配置 - 使用不常用端口（默认 5010）
// 优先读取新的环境变量 VITE_API_BASE_URL_ALT，兼容旧的 VITE_API_BASE_URL
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL_ALT ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:5010';

// HTTP请求辅助函数
class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        // 尝试解析错误响应
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData: ApiError = await response.json();
          errorMessage = errorData.message || errorMessage;
        } catch {
          // 如果无法解析错误响应，使用默认错误消息
        }
        throw new Error(errorMessage);
      }

      const data: ApiResponse<T> = await response.json();

      if (!data.success) {
        throw new Error(data.message || '请求失败');
      }

      return data.data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('网络请求失败');
    }
  }

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(endpoint, this.baseURL);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return this.request<T>(url.pathname + url.search);
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    });
  }
}

const apiClient = new ApiClient(API_BASE_URL);

// 角色API服务
export const roleApi = {
  /**
   * 获取角色列表
   */
  async getRoles(params?: RoleListParams): Promise<RoleListResult> {
    const queryParams = {
      search: params?.keyword, // 后端使用search参数而非keyword
      page: params?.page || 1,
      page_size: params?.page_size || 20,
      type: params?.type,
    };

    const response = await apiClient.get<RoleListResponse>('/api/roles', queryParams);

    return {
      items: response.roles,
      total: response.total,
      page: response.page,
      page_size: response.page_size,
    };
  },

  /**
   * 获取角色详情
   */
  async getRole(id: number): Promise<Role> {
    return apiClient.get<Role>(`/api/roles/${id}`);
  },

  /**
   * 创建新角色
   */
  async createRole(roleData: RoleRequest): Promise<Role> {
    return apiClient.post<Role>('/api/roles', roleData);
  },

  /**
   * 更新角色
   */
  async updateRole(id: number, roleData: RoleRequest): Promise<Role> {
    return apiClient.put<Role>(`/api/roles/${id}`, roleData);
  },

  /**
   * 删除角色
   */
  async deleteRole(id: number): Promise<void> {
    return apiClient.delete<void>(`/api/roles/${id}`);
  },
};

// 导出API客户端以供其他模块使用
export { apiClient };

// 导出API基础URL以便调试
export { API_BASE_URL };
