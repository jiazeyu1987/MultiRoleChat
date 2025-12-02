// 角色相关的TypeScript类型定义

export interface Role {
  id: number;
  name: string;
  prompt: string;
  created_at: string;
  updated_at?: string;
}

// 角色创建/更新请求类型
export interface RoleRequest {
  name: string;
  prompt: string;
}

// 角色列表查询参数
export interface RoleListParams {
  keyword?: string;
  page?: number;
  page_size?: number;
  type?: string;
}

// 后端API响应的基础类型
export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
  error_code?: string;
}

// 角色列表响应数据类型
export interface RoleListResponse {
  roles: Role[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// 前端组件内部使用的角色列表类型
export interface RoleListResult {
  items: Role[];
  total: number;
  page?: number;
  page_size?: number;
}

// API错误类型
export interface ApiError {
  success: false;
  error_code: string;
  message: string;
}

// 角色类型枚举（基于后端Schema）
export type RoleType = 'teacher' | 'student' | 'expert' | 'reviewer' | 'official' | 'lawyer' | 'other';