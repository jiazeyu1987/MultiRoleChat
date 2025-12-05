import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { debounce, throttle } from 'lodash-es';

interface PerformanceConfig {
  enableVirtualScrolling: boolean;
  enableItemCaching: boolean;
  enableRequestDeduplication: boolean;
  enableLazyLoading: boolean;
  enableMemoryOptimization: boolean;
  maxCacheSize: number;
  debounceDelay: number;
  throttleDelay: number;
  virtualScrollThreshold: number;
  lazyLoadThreshold: number;
}

interface CacheItem<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

interface RequestCache {
  [key: string]: {
    promise: Promise<any>;
    timestamp: number;
    ttl: number;
  };
}

interface VirtualScrollItem {
  id: string | number;
  height: number;
  data: any;
}

const defaultPerformanceConfig: PerformanceConfig = {
  enableVirtualScrolling: true,
  enableItemCaching: true,
  enableRequestDeduplication: true,
  enableLazyLoading: true,
  enableMemoryOptimization: true,
  maxCacheSize: 100,
  debounceDelay: 300,
  throttleDelay: 100,
  virtualScrollThreshold: 50,
  lazyLoadThreshold: 20
};

/**
 * 性能优化Hook
 */
export const usePerformanceOptimizations = (config: Partial<PerformanceConfig> = {}) => {
  const performanceConfig = { ...defaultPerformanceConfig, ...config };

  // 缓存相关
  const cacheRef = useRef<Map<string, CacheItem<any>>>(new Map());
  const requestCacheRef = useRef<RequestCache>({});

  // 内存使用监控
  const memoryUsageRef = useRef<{
    items: number;
    size: number;
    lastCleanup: number;
  }>({
    items: 0,
    size: 0,
    lastCleanup: Date.now()
  });

  // 清理过期缓存
  const cleanupCache = useCallback(() => {
    const now = Date.now();
    const cache = cacheRef.current;

    cache.forEach((item, key) => {
      if (now - item.timestamp > item.ttl) {
        cache.delete(key);
      }
    });

    // 如果缓存仍然过大，删除最旧的项目
    if (cache.size > performanceConfig.maxCacheSize) {
      const entries = Array.from(cache.entries())
        .sort((a, b) => a[1].timestamp - b[1].timestamp);

      const toDelete = entries.slice(0, cache.size - performanceConfig.maxCacheSize);
      toDelete.forEach(([key]) => cache.delete(key));
    }

    memoryUsageRef.current = {
      items: cache.size,
      size: JSON.stringify([...cache.entries()]).length,
      lastCleanup: now
    };
  }, [performanceConfig.maxCacheSize]);

  // 定期清理缓存
  useEffect(() => {
    if (!performanceConfig.enableItemCaching) return;

    const interval = setInterval(cleanupCache, 60000); // 每分钟清理一次
    return () => clearInterval(interval);
  }, [cleanupCache, performanceConfig.enableItemCaching]);

  // 缓存操作
  const cacheOperations = {
    get: useCallback(<T>(key: string): T | null => {
      if (!performanceConfig.enableItemCaching) return null;

      const item = cacheRef.current.get(key);
      if (!item) return null;

      const now = Date.now();
      if (now - item.timestamp > item.ttl) {
        cacheRef.current.delete(key);
        return null;
      }

      return item.data;
    }, [performanceConfig.enableItemCaching]),

    set: useCallback(<T>(key: string, data: T, ttl: number = 300000): void => {
      if (!performanceConfig.enableItemCaching) return;

      cacheRef.current.set(key, {
        data,
        timestamp: Date.now(),
        ttl
      });
    }, [performanceConfig.enableItemCaching]),

    delete: useCallback((key: string): void => {
      if (!performanceConfig.enableItemCaching) return;
      cacheRef.current.delete(key);
    }, [performanceConfig.enableItemCaching]),

    clear: useCallback((): void => {
      if (!performanceConfig.enableItemCaching) return;
      cacheRef.current.clear();
    }, [performanceConfig.enableItemCaching])
  };

  // 请求去重
  const deduplicateRequest = useCallback(
    <T>(key: string, requestFn: () => Promise<T>, ttl: number = 5000): Promise<T> => {
      if (!performanceConfig.enableRequestDeduplication) {
        return requestFn();
      }

      const now = Date.now();
      const cached = requestCacheRef.current[key];

      // 检查是否有相同的请求正在进行
      if (cached && now - cached.timestamp < cached.ttl) {
        return cached.promise;
      }

      // 执行请求并缓存结果
      const promise = requestFn();
      requestCacheRef.current[key] = {
        promise,
        timestamp: now,
        ttl
      };

      // 清理过期的请求缓存
      setTimeout(() => {
        delete requestCacheRef.current[key];
      }, ttl);

      return promise;
    },
    [performanceConfig.enableRequestDeduplication]
  );

  // 防抖函数
  const createDebouncedFn = useCallback(
    <T extends (...args: any[]) => any>(fn: T, delay?: number): T => {
      return debounce(fn, delay || performanceConfig.debounceDelay) as T;
    },
    [performanceConfig.debounceDelay]
  );

  // 节流函数
  const createThrottledFn = useCallback(
    <T extends (...args: any[]) => any>(fn: T, delay?: number): T => {
      return throttle(fn, delay || performanceConfig.throttleDelay) as T;
    },
    [performanceConfig.throttleDelay]
  );

  return {
    config: performanceConfig,
    cache: cacheOperations,
    deduplicateRequest,
    createDebouncedFn,
    createThrottledFn,
    cleanupCache,
    memoryUsage: memoryUsageRef.current
  };
};

/**
 * 虚拟滚动Hook
 */
export const useVirtualScroll = (
  items: any[],
  itemHeight: number = 50,
  containerHeight: number = 400,
  overscan: number = 5
) => {
  const [scrollTop, setScrollTop] = useState(0);

  const visibleRange = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      items.length,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
    );

    return { startIndex, endIndex };
  }, [scrollTop, itemHeight, containerHeight, overscan, items.length]);

  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.startIndex, visibleRange.endIndex).map((item, index) => ({
      item,
      index: visibleRange.startIndex + index,
      top: (visibleRange.startIndex + index) * itemHeight
    }));
  }, [items, visibleRange, itemHeight]);

  const totalHeight = items.length * itemHeight;

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight,
    startIndex: visibleRange.startIndex,
    endIndex: visibleRange.endIndex,
    handleScroll,
    scrollTop
  };
};

/**
 * 懒加载Hook
 */
export const useLazyLoad = (
  threshold: number = 20,
  initialLoadCount: number = 10
) => {
  const [loadedCount, setLoadedCount] = useState(initialLoadCount);
  const [isLoading, setIsLoading] = useState(false);

  const loadMore = useCallback(async () => {
    if (isLoading) return;

    setIsLoading(true);
    // 模拟异步加载
    await new Promise(resolve => setTimeout(resolve, 500));
    setLoadedCount(prev => prev + threshold);
    setIsLoading(false);
  }, [isLoading, threshold]);

  const reset = useCallback(() => {
    setLoadedCount(initialLoadCount);
    setIsLoading(false);
  }, [initialLoadCount]);

  return {
    loadedCount,
    isLoading,
    loadMore,
    reset
  };
};

/**
 * 内存监控Hook
 */
export const useMemoryMonitor = () => {
  const [memoryStats, setMemoryStats] = useState({
    usedJSHeapSize: 0,
    totalJSHeapSize: 0,
    jsHeapSizeLimit: 0
  });

  const updateMemoryStats = useCallback(() => {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      setMemoryStats({
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      });
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(updateMemoryStats, 5000);
    updateMemoryStats();
    return () => clearInterval(interval);
  }, [updateMemoryStats]);

  const memoryUsagePercentage = useMemo(() => {
    if (memoryStats.jsHeapSizeLimit === 0) return 0;
    return (memoryStats.usedJSHeapSize / memoryStats.jsHeapSizeLimit) * 100;
  }, [memoryStats]);

  return {
    memoryStats,
    memoryUsagePercentage,
    updateMemoryStats
  };
};

/**
 * 性能监控Hook
 */
export const usePerformanceMonitor = () => {
  const [metrics, setMetrics] = useState({
    renderTime: 0,
    componentCount: 0,
    reRenderCount: 0,
    lastRenderTime: 0
  });

  const renderStartTime = useRef<number>(0);
  const reRenderCount = useRef<number>(0);

  const startRenderMeasure = useCallback(() => {
    renderStartTime.current = performance.now();
    reRenderCount.current += 1;
  }, []);

  const endRenderMeasure = useCallback(() => {
    const renderTime = performance.now() - renderStartTime.current;
    setMetrics(prev => ({
      ...prev,
      renderTime,
      reRenderCount: reRenderCount.current,
      lastRenderTime: Date.now()
    }));
  }, []);

  const measureComponent = useCallback((componentName: string) => {
    return (WrappedComponent: React.ComponentType<any>) => {
      return (props: any) => {
        startRenderMeasure();
        const result = <WrappedComponent {...props} />;
        endRenderMeasure();
        return result;
      };
    };
  }, [startRenderMeasure, endRenderMeasure]);

  return {
    metrics,
    startRenderMeasure,
    endRenderMeasure,
    measureComponent
  };
};

/**
 * 智能缓存Hook
 */
export const useSmartCache = <T>(key: string, fetcher: () => Promise<T>, ttl: number = 300000) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const cache = useRef<Map<string, CacheItem<T>>>(new Map());

  const fetch = useCallback(async (forceRefresh = false) => {
    const cached = cache.current.get(key);
    const now = Date.now();

    // 检查缓存
    if (!forceRefresh && cached && now - cached.timestamp < cached.ttl) {
      setData(cached.data);
      return cached.data;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await fetcher();

      // 更新缓存
      cache.current.set(key, {
        data: result,
        timestamp: now,
        ttl
      });

      setData(result);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [key, fetcher, ttl]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const invalidate = useCallback(() => {
    cache.current.delete(key);
  }, [key]);

  const refresh = useCallback(() => {
    return fetch(true);
  }, [fetch]);

  return {
    data,
    loading,
    error,
    fetch,
    invalidate,
    refresh
  };
};

/**
 * 优化列表Hook
 */
export const useOptimizedList = <T>(
  items: T[],
  options: {
    enableVirtualScroll?: boolean;
    enableItemCache?: boolean;
    itemHeight?: number;
    containerHeight?: number;
    getItemKey?: (item: T, index: number) => string | number;
  } = {}
) => {
  const {
    enableVirtualScroll = true,
    enableItemCache = true,
    itemHeight = 50,
    containerHeight = 400,
    getItemKey = (item, index) => index
  } = options;

  const [visibleItems, setVisibleItems] = useState<T[]>(items);
  const itemCache = useRef<Map<string | number, T>>(new Map());

  // 更新可见项目
  useEffect(() => {
    if (enableVirtualScroll && items.length > 50) {
      // 虚拟滚动逻辑
      setVisibleItems(items.slice(0, 20)); // 简化版，实际应该基于滚动位置
    } else {
      setVisibleItems(items);
    }

    // 更新缓存
    if (enableItemCache) {
      items.forEach((item, index) => {
        itemCache.current.set(getItemKey(item, index), item);
      });
    }
  }, [items, enableVirtualScroll, enableItemCache, getItemKey]);

  const getCachedItem = useCallback((key: string | number): T | undefined => {
    return itemCache.current.get(key);
  }, []);

  return {
    visibleItems,
    getCachedItem,
    itemCount: items.length,
    isVirtualScrolling: enableVirtualScroll && items.length > 50
  };
};

export default usePerformanceOptimizations;