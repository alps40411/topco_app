// frontend/src/hooks/useDataSync.ts
import { useCallback } from 'react';

interface UseSyncOptions {
  debounceMs?: number;
  maxConcurrent?: number;
}

export const useDataSync = (options: UseSyncOptions = {}) => {
  // 簡化：直接並行執行，不加複雜的控制邏輯
  const batchSync = useCallback(async (syncFunctions: Array<() => Promise<void>>) => {
    try {
      await Promise.all(syncFunctions.map(fn => fn()));
    } catch (error) {
      console.warn('Batch sync failed:', error);
    }
  }, []);

  // 提供基本的同步函數（移除複雜邏輯）
  const immediateSync = useCallback(async (syncFunction: () => Promise<void>) => {
    try {
      await syncFunction();
    } catch (error) {
      console.warn('Sync failed:', error);
    }
  }, []);

  return {
    batchSync,
    immediateSync
  };
};