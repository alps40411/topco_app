// frontend/src/utils/weekUtils.ts

import {
  getISOWeek,
  getISOWeekYear,
  startOfISOWeek,
  endOfISOWeek,
  setISOWeek,
  addWeeks,
} from "date-fns";

// 重新導出 date-fns 的 ISO 週次函數供其他模組使用
export { getISOWeek, getISOWeekYear };

/**
 * 獲取指定周的起始日期（週一）- ISO 8601 標準
 * @param year ISO 年份
 * @param week ISO 週次（1-53）
 * @returns 週一日期
 */
export function getWeekStartDate(year: number, week: number): Date {
  // ISO 8601：第 1 周包含該年第一個週四（即 1/4）
  // 找到該年 1/4 所在週的週一
  const jan4 = new Date(year, 0, 4);
  const firstWeekMonday = startOfISOWeek(jan4);

  // 加上指定的週數
  return addWeeks(firstWeekMonday, week - 1);
}

/**
 * 獲取指定周的結束日期（週日）- ISO 8601 標準
 * @param year ISO 年份
 * @param week ISO 週次（1-53）
 * @returns 週日日期
 */
export function getWeekEndDate(year: number, week: number): Date {
  const weekStart = getWeekStartDate(year, week);
  return endOfISOWeek(weekStart);
}

/**
 * 格式化週次範圍為字串 - ISO 8601 標準
 * 例如：formatWeekRange(2025, 24) => "06/09 ~ 06/15"
 * 跨年：formatWeekRange(2026, 1) => "12/29 ~ 01/04"
 * @param year ISO 年份
 * @param week ISO 週次
 * @returns 格式化的日期範圍字串（不含年份）
 */
export function formatWeekRange(year: number, week: number): string {
  const start = getWeekStartDate(year, week);
  const end = getWeekEndDate(year, week);

  const startMonth = start.getMonth() + 1;
  const startDay = start.getDate();
  const endMonth = end.getMonth() + 1;
  const endDay = end.getDate();

  const formatDate = (m: number, d: number) =>
    `${String(m).padStart(2, '0')}/${String(d).padStart(2, '0')}`;

  // 統一格式，不顯示年份
  return `${formatDate(startMonth, startDay)} ~ ${formatDate(endMonth, endDay)}`;
}

/**
 * 獲取當前周次 - 自訂義邏輯（週一 08:30 切換）
 *
 * 業務規則：
 * - 週一 00:00 ~ 08:30：仍屬於上一週
 * - 週一 08:30 之後：切換到新的一週
 * - 其他時間：使用 ISO 8601 標準
 *
 * @returns { year: ISO 年份, week: ISO 週次 }
 */
export function getCurrentWeek(): { year: number; week: number } {
  const now = new Date();
  const dayOfWeek = now.getDay(); // 0 = 週日, 1 = 週一, 2 = 週二, ...
  const hours = now.getHours();
  const minutes = now.getMinutes();

  // 如果是週一 00:00 ~ 08:30，返回上一週
  if (dayOfWeek === 1 && (hours < 8 || (hours === 8 && minutes < 30))) {
    // 減去一天，讓 getISOWeek 計算上一週
    const lastWeek = new Date(now);
    lastWeek.setDate(lastWeek.getDate() - 1);

    return {
      year: getISOWeekYear(lastWeek),
      week: getISOWeek(lastWeek)
    };
  }

  // 其他時間使用標準 ISO 週次
  return {
    year: getISOWeekYear(now),
    week: getISOWeek(now)
  };
}

/**
 * 獲取指定週次的前後N周列表
 * @param year 中心年份
 * @param week 中心週次
 * @param count 顯示的週次數量
 * @returns 週次列表
 */
export function getWeekRange(
  year: number,
  week: number,
  count: number
): Array<{ year: number; week: number }> {
  const result: Array<{ year: number; week: number }> = [];
  const seen = new Set<string>(); // 用於去重
  const halfCount = Math.floor(count / 2);

  // 從當前週往前推
  for (let i = halfCount; i > 0; i--) {
    const targetDate = addWeeks(getWeekStartDate(year, week), -i);
    const y = getISOWeekYear(targetDate);
    const w = getISOWeek(targetDate);
    const key = `${y}-${w}`;

    if (!seen.has(key)) {
      seen.add(key);
      result.push({ year: y, week: w });
    }
  }

  // 當前週
  const currentKey = `${year}-${week}`;
  if (!seen.has(currentKey)) {
    seen.add(currentKey);
    result.push({ year, week });
  }

  // 從當前週往後推
  for (let i = 1; i < count - halfCount; i++) {
    const targetDate = addWeeks(getWeekStartDate(year, week), i);
    const y = getISOWeekYear(targetDate);
    const w = getISOWeek(targetDate);
    const key = `${y}-${w}`;

    if (!seen.has(key)) {
      seen.add(key);
      result.push({ year: y, week: w });
    }
  }

  return result;
}
