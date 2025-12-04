// 错误处理工具
export interface ApiError {
  response?: {
    data?: {
      message?: string;
      error_code?: string;
      details?: any;
    };
    status?: number;
  };
  message?: string;
  code?: string;
}

export class ApiErrorHandler {
  /**
   * 从API错误中提取用户友好的错误消息
   */
  static extractMessage(error: any): string {
    // 如果是响应错误，优先使用服务器返回的消息
    if (error?.response?.data?.message) {
      let message = error.response.data.message;
      // 如果有详细信息，也显示出来
      if (error.response.data.details) {
        message += ` (${error.response.data.details})`;
      }
      return message;
    }

    // 如果是网络错误
    if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('Network Error')) {
      return '网络连接失败，请检查网络后重试';
    }

    // 如果是超时错误
    if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
      return '请求超时，请重试';
    }

    // 如果是服务器错误
    if (error?.response?.status === 500) {
      return '服务器内部错误，请稍后重试';
    }

    if (error?.response?.status === 404) {
      return '请求的资源不存在';
    }

    if (error?.response?.status === 401) {
      return '未授权访问，请重新登录';
    }

    if (error?.response?.status === 403) {
      return '权限不足，无法执行此操作';
    }

    if (error?.response?.status === 400) {
      return '请求参数错误，请检查输入信息';
    }

    // 默认错误消息
    return error?.message || '操作失败，请重试';
  }

  /**
   * 获取错误的详细信息（用于调试）
   */
  static getDetails(error: any): any {
    return {
      message: this.extractMessage(error),
      code: error?.response?.data?.error_code || error?.code,
      status: error?.response?.status,
      details: error?.response?.data?.details,
      originalError: error
    };
  }

  /**
   * 处理API错误并显示用户友好的消息
   */
  static handle(error: any, showMessage: boolean = true): string {
    const message = this.extractMessage(error);

    // 记录详细错误信息到控制台（用于调试）
    console.error('API Error:', this.getDetails(error));

    if (showMessage) {
      // 使用更友好的错误显示方式
      this.showUserMessage(message);
    }

    return message;
  }

  /**
   * 显示用户友好的错误消息
   */
  static showUserMessage(message: string, type: 'error' | 'warning' | 'info' = 'error') {
    // 如果浏览器支持通知API
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Multi-Role Chat', {
        body: message,
        icon: '/favicon.ico'
      });
    } else {
      // 回退到alert，但将来可以替换为更好的UI组件
      alert(message);
    }
  }

  /**
   * 显示成功消息
   */
  static showSuccess(message: string) {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('操作成功', {
        body: message,
        icon: '/favicon.ico'
      });
    } else {
      // 这里可以使用toast或通知组件
      console.log('Success:', message);
    }
  }
}

// 便捷的错误处理函数
export const handleError = (error: any, showMessage: boolean = true): string => {
  return ApiErrorHandler.handle(error, showMessage);
};

// 便捷的成功处理函数
export const showSuccess = (message: string) => {
  ApiErrorHandler.showSuccess(message);
};