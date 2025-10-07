// frontend/src/hooks/useWorkData.ts

import { useContext } from 'react';
import { WorkDataContext } from '../contexts/WorkDataContext';

export const useWorkData = () => {
  const context = useContext(WorkDataContext);
  if (context === undefined) {
    throw new Error('useWorkData 必須在 WorkDataProvider 內使用');
  }
  return context;
};
