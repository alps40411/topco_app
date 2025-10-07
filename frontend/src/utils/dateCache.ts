// frontend/src/utils/dateCache.ts

interface DateOption {
  value: string;
  display: string;
  date: string;
  is_weekday: boolean;
  is_today: boolean;
  is_default: boolean;
  can_write: boolean;
  status: string;
}

// 全局緩存日期數據
export let globalDateCache: {
  data: DateOption[];
  currentReportDate: string;
  timestamp: number;
  isLoading?: boolean;
} | null = null;

export const CACHE_DURATION = 5 * 60 * 1000; // 5分鐘緩存

// 清除快取函數，供登入頁面使用
export const clearDateCache = () => {
  globalDateCache = null;
};

// 設置快取
export const setDateCache = (cache: typeof globalDateCache) => {
  globalDateCache = cache;
};

// 獲取快取
export const getDateCache = () => globalDateCache;
