// frontend/src/utils/timeUtils.ts

/**
 * 將分鐘轉換為小時制顯示（如 1.25 小時）
 * @param minutes 分鐘數
 * @returns 格式化的時間字串
 */
export const formatMinutesToHours = (minutes: number): string => {
  if (minutes === 0) return "0 小時";
  const hours = minutes / 60;
  return `${hours.toFixed(2)} 小時`;
};

/**
 * 將分鐘轉換為小時制顯示（不包含單位）
 * @param minutes 分鐘數
 * @returns 小時數（保留兩位小數）
 */
export const minutesToHours = (minutes: number): number => {
  return Math.round((minutes / 60) * 100) / 100; // 四捨五入到小數點後兩位
};

/**
 * 將小時轉換為分鐘
 * @param hours 小時數
 * @returns 分鐘數
 */
export const hoursToMinutes = (hours: number): number => {
  return Math.round(hours * 60);
};