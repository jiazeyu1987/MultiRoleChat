import { useState, useEffect, useCallback } from 'react';

export interface UserPreferences {
  // 界面设置
  theme: 'light' | 'dark' | 'auto';
  language: 'zh-CN' | 'en-US';
  compactMode: boolean;

  // 调试面板设置
  enableDebugPanel: boolean;
  debugPanelPosition: 'fixed' | 'relative';
  debugPanelSize: 'small' | 'medium' | 'large';
  debugPanelAutoRefresh: boolean;
  debugPanelRefreshInterval: number;
  showAdvancedDebug: boolean;

  // 实时更新设置
  enableRealtimeUpdates: boolean;
  websocketAutoReconnect: boolean;
  maxReconnectAttempts: number;

  // 步骤进度设置
  enableStepProgress: boolean;
  stepProgressAutoRefresh: boolean;
  stepProgressRefreshInterval: number;
  showStepDetails: boolean;
  showPerformanceMetrics: boolean;

  // LLM调试设置
  enableLLMDebug: boolean;
  showLLMStreaming: boolean;
  showLLMDetails: boolean;
  showLLMDebugInfo: boolean;
  maxLLMItems: number;
  llmRefreshInterval: number;

  // 可视化设置
  defaultVisualizationMode: 'flow' | 'timeline' | 'tree';
  showVisualizationPerformance: boolean;
  enableInteractiveVisualization: boolean;

  // 性能优化设置
  enableVirtualScrolling: boolean;
  enableItemCaching: boolean;
  enableRequestDeduplication: boolean;
  maxCacheSize: number;

  // 通知设置
  enableNotifications: boolean;
  notifyOnStepComplete: boolean;
  notifyOnLLMError: boolean;
  notifyOnSystemError: boolean;

  // 数据导出设置
  autoExportEnabled: boolean;
  exportFormat: 'json' | 'csv' | 'txt';
  exportIncludeDebugInfo: boolean;

  // 隐私设置
  shareUsageData: boolean;
  shareErrorReports: boolean;
  anonymizeSharedData: boolean;
}

const defaultPreferences: UserPreferences = {
  // 界面设置
  theme: 'light',
  language: 'zh-CN',
  compactMode: false,

  // 调试面板设置
  enableDebugPanel: true,
  debugPanelPosition: 'fixed',
  debugPanelSize: 'medium',
  debugPanelAutoRefresh: true,
  debugPanelRefreshInterval: 2000,
  showAdvancedDebug: false,

  // 实时更新设置
  enableRealtimeUpdates: true,
  websocketAutoReconnect: true,
  maxReconnectAttempts: 5,

  // 步骤进度设置
  enableStepProgress: true,
  stepProgressAutoRefresh: true,
  stepProgressRefreshInterval: 3000,
  showStepDetails: true,
  showPerformanceMetrics: true,

  // LLM调试设置
  enableLLMDebug: true,
  showLLMStreaming: true,
  showLLMDetails: true,
  showLLMDebugInfo: false,
  maxLLMItems: 50,
  llmRefreshInterval: 3000,

  // 可视化设置
  defaultVisualizationMode: 'flow',
  showVisualizationPerformance: true,
  enableInteractiveVisualization: true,

  // 性能优化设置
  enableVirtualScrolling: true,
  enableItemCaching: true,
  enableRequestDeduplication: true,
  maxCacheSize: 100,

  // 通知设置
  enableNotifications: true,
  notifyOnStepComplete: true,
  notifyOnLLMError: true,
  notifyOnSystemError: true,

  // 数据导出设置
  autoExportEnabled: false,
  exportFormat: 'json',
  exportIncludeDebugInfo: false,

  // 隐私设置
  shareUsageData: false,
  shareErrorReports: false,
  anonymizeSharedData: true
};

interface UseUserPreferencesOptions {
  userId?: string | null;
  storageKey?: string;
  enablePersistence?: boolean;
  enableCloudSync?: boolean;
}

interface UseUserPreferencesReturn {
  preferences: UserPreferences;
  updatePreference: <K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => void;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  resetToDefaults: () => void;
  exportPreferences: () => string;
  importPreferences: (data: string) => boolean;
  isLoading: boolean;
  error: string | null;
  saveToCloud: () => Promise<void>;
  loadFromCloud: () => Promise<void>;
}

/**
 * 用户偏好设置Hook
 */
export const useUserPreferences = ({
  userId,
  storageKey = 'user-preferences',
  enablePersistence = true,
  enableCloudSync = false
}: UseUserPreferencesOptions = {}): UseUserPreferencesReturn => {
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 存储键（包含用户ID以支持多用户）
  const actualStorageKey = userId ? `${storageKey}-${userId}` : storageKey;

  // 从本地存储加载偏好设置
  const loadFromStorage = useCallback(() => {
    try {
      const stored = localStorage.getItem(actualStorageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        // 合并默认设置和存储的设置
        const merged = { ...defaultPreferences, ...parsed };
        setPreferences(merged);
      } else {
        setPreferences(defaultPreferences);
      }
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load preferences';
      setError(errorMessage);
      console.error('Failed to load user preferences:', err);
      setPreferences(defaultPreferences);
    } finally {
      setIsLoading(false);
    }
  }, [actualStorageKey]);

  // 保存到本地存储
  const saveToStorage = useCallback((prefs: UserPreferences) => {
    if (!enablePersistence) return;

    try {
      localStorage.setItem(actualStorageKey, JSON.stringify(prefs));
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save preferences';
      setError(errorMessage);
      console.error('Failed to save user preferences:', err);
    }
  }, [actualStorageKey, enablePersistence]);

  // 更新单个偏好设置
  const updatePreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => {
      const updated = { ...prev, [key]: value };
      saveToStorage(updated);
      return updated;
    });
  }, [saveToStorage]);

  // 批量更新偏好设置
  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setPreferences(prev => {
      const updated = { ...prev, ...updates };
      saveToStorage(updated);
      return updated;
    });
  }, [saveToStorage]);

  // 重置偏好设置（使用默认值但保留某些关键设置）
  const resetPreferences = useCallback(() => {
    const reset = {
      ...defaultPreferences,
      // 保留用户相关的设置
      theme: preferences.theme,
      language: preferences.language,
      compactMode: preferences.compactMode
    };
    setPreferences(reset);
    saveToStorage(reset);
  }, [preferences, saveToStorage]);

  // 重置为默认值
  const resetToDefaults = useCallback(() => {
    setPreferences(defaultPreferences);
    saveToStorage(defaultPreferences);
  }, [saveToStorage]);

  // 导出偏好设置
  const exportPreferences = useCallback((): string => {
    try {
      const exportData = {
        preferences,
        exportedAt: new Date().toISOString(),
        version: '1.0'
      };
      return JSON.stringify(exportData, null, 2);
    } catch (err) {
      setError('Failed to export preferences');
      return '';
    }
  }, [preferences]);

  // 导入偏好设置
  const importPreferences = useCallback((data: string): boolean => {
    try {
      const parsed = JSON.parse(data);
      if (parsed.preferences && typeof parsed.preferences === 'object') {
        const imported = { ...defaultPreferences, ...parsed.preferences };
        setPreferences(imported);
        saveToStorage(imported);
        setError(null);
        return true;
      }
      return false;
    } catch (err) {
      setError('Failed to import preferences: Invalid format');
      return false;
    }
  }, [saveToStorage]);

  // 保存到云端（模拟）
  const saveToCloud = useCallback(async (): Promise<void> => {
    if (!enableCloudSync || !userId) {
      throw new Error('Cloud sync is not enabled or user not logged in');
    }

    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 这里应该调用实际的API
      console.log('Saving preferences to cloud for user:', userId);

      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save to cloud';
      setError(errorMessage);
      throw err;
    }
  }, [enableCloudSync, userId]);

  // 从云端加载（模拟）
  const loadFromCloud = useCallback(async (): Promise<void> => {
    if (!enableCloudSync || !userId) {
      throw new Error('Cloud sync is not enabled or user not logged in');
    }

    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 这里应该调用实际的API
      console.log('Loading preferences from cloud for user:', userId);

      // 模拟从云端获取的偏好设置
      const cloudPreferences = { ...defaultPreferences, theme: 'dark' };
      setPreferences(cloudPreferences);
      saveToStorage(cloudPreferences);

      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load from cloud';
      setError(errorMessage);
      throw err;
    }
  }, [enableCloudSync, userId, saveToStorage]);

  // 初始化时加载偏好设置
  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return {
    preferences,
    updatePreference,
    updatePreferences,
    resetPreferences,
    resetToDefaults,
    exportPreferences,
    importPreferences,
    isLoading,
    error,
    saveToCloud,
    loadFromCloud
  };
};

/**
 * 偏好设置上下文
 */
import { createContext, useContext, ReactNode } from 'react';

interface PreferencesContextValue {
  preferences: UserPreferences;
  updatePreference: <K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => void;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  isLoading: boolean;
  error: string | null;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export const PreferencesProvider: React.FC<{
  children: ReactNode;
  userId?: string | null;
  enablePersistence?: boolean;
  enableCloudSync?: boolean;
}> = ({ children, userId, enablePersistence, enableCloudSync }) => {
  const preferencesHook = useUserPreferences({
    userId,
    enablePersistence,
    enableCloudSync
  });

  return (
    <PreferencesContext.Provider value={preferencesHook}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferencesContext = (): PreferencesContextValue => {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferencesContext must be used within a PreferencesProvider');
  }
  return context;
};

/**
 * 主题Hook
 */
export const useTheme = () => {
  const { preferences, updatePreference } = usePreferencesContext();

  const setTheme = (theme: UserPreferences['theme']) => {
    updatePreference('theme', theme);

    // 应用主题到DOM
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  useEffect(() => {
    // 初始化时应用主题
    if (preferences.theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  }, [preferences.theme]);

  return {
    theme: preferences.theme,
    setTheme,
    isDark: preferences.theme === 'dark'
  };
};

/**
 * 通知Hook
 */
export const useNotifications = () => {
  const { preferences } = usePreferencesContext();

  const showNotification = useCallback((
    title: string,
    message: string,
    type: 'info' | 'success' | 'warning' | 'error' = 'info'
  ) => {
    if (!preferences.enableNotifications) return;

    // 检查浏览器通知支持
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body: message,
        icon: type === 'error' ? '/error-icon.png' : '/info-icon.png'
      });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification(title, { body: message });
        }
      });
    }

    // 如果浏览器不支持或被拒绝，使用console作为fallback
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
  }, [preferences.enableNotifications]);

  return { showNotification };
};

/**
 * 自动导出Hook
 */
export const useAutoExport = (sessionId?: number) => {
  const { preferences } = usePreferencesContext();

  useEffect(() => {
    if (!preferences.autoExportEnabled || !sessionId) return;

    const interval = setInterval(() => {
      // 触发自动导出逻辑
      console.log(`Auto-exporting session ${sessionId} data`);

      // 这里应该实现实际的导出逻辑
      // 例如：调用导出API，下载数据等
    }, 300000); // 每5分钟导出一次

    return () => clearInterval(interval);
  }, [preferences.autoExportEnabled, sessionId]);
};

export default useUserPreferences;