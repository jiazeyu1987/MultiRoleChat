import { useState, useEffect, useCallback } from 'react';

export type Permission =
  | 'session:read'
  | 'session:write'
  | 'session:delete'
  | 'session:execute'
  | 'debug:view'
  | 'debug:advanced'
  | 'llm:view'
  | 'llm:details'
  | 'system:monitor'
  | 'flow:edit'
  | 'role:manage';

export interface UserPermissions {
  userId?: string | null;
  roles: string[];
  permissions: Set<Permission>;
  isAdmin: boolean;
  isDeveloper: boolean;
}

interface PermissionConfig {
  enablePermissions: boolean;
  defaultPermissions: Permission[];
  adminPermissions: Permission[];
  developerPermissions: Permission[];
  debugPermissions: Permission[];
}

const defaultPermissionConfig: PermissionConfig = {
  enablePermissions: true,
  defaultPermissions: [
    'session:read',
    'session:execute',
    'debug:view',
    'llm:view'
  ],
  adminPermissions: [
    'session:delete',
    'system:monitor',
    'role:manage',
    'flow:edit'
  ],
  developerPermissions: [
    'debug:advanced',
    'llm:details',
    'session:write',
    'system:monitor'
  ],
  debugPermissions: [
    'debug:view',
    'debug:advanced',
    'llm:details',
    'system:monitor'
  ]
};

interface UsePermissionsOptions {
  userId?: string | null;
  roles?: string[];
  config?: Partial<PermissionConfig>;
  enableCache?: boolean;
}

interface UsePermissionsReturn {
  permissions: UserPermissions;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
  canAccessDebugPanel: boolean;
  canViewLLMDetails: boolean;
  canExecuteSteps: boolean;
  canManageSystem: boolean;
  canEditFlows: boolean;
  isLoading: boolean;
  error: string | null;
  refreshPermissions: () => Promise<void>;
}

// 模拟权限数据存储（在实际应用中应该从API获取）
const mockUserPermissions: Record<string, Partial<UserPermissions>> = {
  'admin': {
    isAdmin: true,
    isDeveloper: true,
    roles: ['admin', 'developer']
  },
  'developer': {
    isAdmin: false,
    isDeveloper: true,
    roles: ['developer']
  },
  'user': {
    isAdmin: false,
    isDeveloper: false,
    roles: ['user']
  }
};

/**
 * 权限管理Hook
 */
export const usePermissions = ({
  userId,
  roles = [],
  config = {},
  enableCache = true
}: UsePermissionsOptions = {}): UsePermissionsReturn => {
  const [permissions, setPermissions] = useState<UserPermissions>({
    userId,
    roles,
    permissions: new Set(defaultPermissionConfig.defaultPermissions),
    isAdmin: false,
    isDeveloper: false
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const permissionConfig = { ...defaultPermissionConfig, ...config };

  // 获取用户权限
  const fetchUserPermissions = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      if (!permissionConfig.enablePermissions) {
        // 如果权限系统被禁用，授予所有权限
        const allPermissions: Permission[] = [
          'session:read', 'session:write', 'session:delete', 'session:execute',
          'debug:view', 'debug:advanced', 'llm:view', 'llm:details',
          'system:monitor', 'flow:edit', 'role:manage'
        ];

        setPermissions({
          userId,
          roles,
          permissions: new Set(allPermissions),
          isAdmin: true,
          isDeveloper: true
        });
        return;
      }

      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 500));

      // 基于用户角色确定权限
      let userPermissions = new Set(permissionConfig.defaultPermissions);
      let isAdmin = false;
      let isDeveloper = false;

      roles.forEach(role => {
        const roleLower = role.toLowerCase();

        if (roleLower === 'admin') {
          isAdmin = true;
          isDeveloper = true;
          permissionConfig.adminPermissions.forEach(perm => userPermissions.add(perm));
        }

        if (roleLower === 'developer') {
          isDeveloper = true;
          permissionConfig.developerPermissions.forEach(perm => userPermissions.add(perm));
        }

        if (roleLower.includes('debug')) {
          permissionConfig.debugPermissions.forEach(perm => userPermissions.add(perm));
        }
      });

      // 检查模拟权限数据
      const mockPerms = mockUserPermissions[userId || ''];
      if (mockPerms) {
        isAdmin = isAdmin || mockPerms.isAdmin || false;
        isDeveloper = isDeveloper || mockPerms.isDeveloper || false;
      }

      setPermissions({
        userId,
        roles,
        permissions: userPermissions,
        isAdmin,
        isDeveloper
      });

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load permissions';
      setError(errorMessage);

      // 失败时使用默认权限
      setPermissions({
        userId,
        roles,
        permissions: new Set(permissionConfig.defaultPermissions),
        isAdmin: false,
        isDeveloper: false
      });
    } finally {
      setIsLoading(false);
    }
  }, [userId, roles, permissionConfig]);

  // 检查单个权限
  const hasPermission = useCallback((permission: Permission): boolean => {
    return permissions.permissions.has(permission);
  }, [permissions.permissions]);

  // 检查是否有任意一个权限
  const hasAnyPermission = useCallback((permissionsToCheck: Permission[]): boolean => {
    return permissionsToCheck.some(perm => permissions.permissions.has(perm));
  }, [permissions.permissions]);

  // 检查是否拥有所有权限
  const hasAllPermissions = useCallback((permissionsToCheck: Permission[]): boolean => {
    return permissionsToCheck.every(perm => permissions.permissions.has(perm));
  }, [permissions.permissions]);

  // 常用权限检查
  const canAccessDebugPanel = hasPermission('debug:view');
  const canViewLLMDetails = hasPermission('llm:details');
  const canExecuteSteps = hasPermission('session:execute');
  const canManageSystem = hasPermission('system:monitor');
  const canEditFlows = hasPermission('flow:edit');

  // 刷新权限
  const refreshPermissions = useCallback(async () => {
    await fetchUserPermissions();
  }, [fetchUserPermissions]);

  useEffect(() => {
    fetchUserPermissions();
  }, [fetchUserPermissions]);

  return {
    permissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canAccessDebugPanel,
    canViewLLMDetails,
    canExecuteSteps,
    canManageSystem,
    canEditFlows,
    isLoading,
    error,
    refreshPermissions
  };
};

/**
 * 权限组件 - 用于条件渲染
 */
interface PermissionGateProps {
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
  children: React.ReactNode;
  onUnauthorized?: () => void;
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  permission,
  permissions = [],
  requireAll = false,
  fallback = null,
  children,
  onUnauthorized
}) => {
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();

  const checkPermission = (): boolean => {
    if (permission) {
      return hasPermission(permission);
    }

    if (permissions.length > 0) {
      return requireAll ? hasAllPermissions(permissions) : hasAnyPermission(permissions);
    }

    return true;
  };

  const hasAccess = checkPermission();

  useEffect(() => {
    if (!hasAccess && onUnauthorized) {
      onUnauthorized();
    }
  }, [hasAccess, onUnauthorized]);

  if (!hasAccess) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

/**
 * 高阶组件 - 为组件添加权限检查
 */
export const withPermissions = <P extends object>(
  WrappedComponent: React.ComponentType<P>,
  requiredPermissions?: Permission[] | Permission,
  requireAll: boolean = false
) => {
  return (props: P) => {
    return (
      <PermissionGate
        permission={typeof requiredPermissions === 'string' ? requiredPermissions : undefined}
        permissions={Array.isArray(requiredPermissions) ? requiredPermissions : undefined}
        requireAll={requireAll}
      >
        <WrappedComponent {...props} />
      </PermissionGate>
    );
  };
};

/**
 * 权限上下文
 */
import { createContext, useContext, ReactNode } from 'react';

interface PermissionContextValue {
  permissions: UserPermissions;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
  refreshPermissions: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const PermissionContext = createContext<PermissionContextValue | null>(null);

export const PermissionProvider: React.FC<{
  children: ReactNode;
  userId?: string | null;
  roles?: string[];
  config?: Partial<PermissionConfig>;
}> = ({ children, userId, roles, config }) => {
  const permissionHook = usePermissions({ userId, roles, config });

  return (
    <PermissionContext.Provider value={permissionHook}>
      {children}
    </PermissionContext.Provider>
  );
};

export const usePermissionContext = (): PermissionContextValue => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error('usePermissionContext must be used within a PermissionProvider');
  }
  return context;
};

/**
 * 权限工具函数
 */
export const permissionUtils = {
  // 检查是否为管理员权限
  isAdminPermission: (permission: Permission): boolean => {
    return permission.includes('delete') || permission.includes('manage');
  },

  // 检查是否为调试权限
  isDebugPermission: (permission: Permission): boolean => {
    return permission.includes('debug') || permission.includes('system:monitor');
  },

  // 获取权限组
  getPermissionGroup: (permission: Permission): string => {
    if (permission.startsWith('session:')) return 'session';
    if (permission.startsWith('debug:')) return 'debug';
    if (permission.startsWith('llm:')) return 'llm';
    if (permission.startsWith('system:')) return 'system';
    if (permission.startsWith('flow:')) return 'flow';
    if (permission.startsWith('role:')) return 'role';
    return 'unknown';
  },

  // 获取权限描述
  getPermissionDescription: (permission: Permission): string => {
    const descriptions: Record<Permission, string> = {
      'session:read': '查看会话',
      'session:write': '编辑会话',
      'session:delete': '删除会话',
      'session:execute': '执行会话步骤',
      'debug:view': '查看调试信息',
      'debug:advanced': '高级调试功能',
      'llm:view': '查看LLM调用',
      'llm:details': '查看LLM详细信息',
      'system:monitor': '系统监控',
      'flow:edit': '编辑流程',
      'role:manage': '管理角色'
    };
    return descriptions[permission] || permission;
  }
};

export default usePermissions;