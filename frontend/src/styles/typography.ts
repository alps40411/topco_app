// frontend/src/styles/typography.ts

/**
 * 統一字體規範標準
 *
 * 目標：所有內文使用 16px，保持視覺一致性
 * 遵循使用者體驗最佳實踐，提供良好的可讀性
 */

export const TypographyStandards = {
  // 主要內容區域 - 16px (text-base)
  content: {
    primary: 'text-base',        // 16px - 表格內容、卡片主文、表單輸入、一般文字
    description: 'text-base',    // 16px - 描述文字、說明文字
    input: 'text-base',          // 16px - 表單輸入框
    tableCell: 'text-base',      // 16px - 表格單元格內容
  },

  // 次要內容區域 - 14px (text-sm)
  secondary: {
    button: 'text-sm',           // 14px - 按鈕文字
    navigation: 'text-sm',       // 14px - 導航項目
    label: 'text-sm',            // 14px - 表單標籤
    menuItem: 'text-sm',         // 14px - 選單項目
  },

  // 小字體區域 - 12px (text-xs)
  small: {
    hint: 'text-xs',             // 12px - 提示文字、說明文字
    status: 'text-xs',           // 12px - 狀態標籤
    timestamp: 'text-xs',        // 12px - 時間戳記
    badge: 'text-xs',            // 12px - 徽章、標籤
    tableHeader: 'text-xs',      // 12px - 表格標題
  },

  // 標題區域
  heading: {
    h1: 'text-2xl',              // 24px - 主標題
    h2: 'text-xl',               // 20px - 副標題
    h3: 'text-lg',               // 18px - 小標題
    cardTitle: 'text-lg',        // 18px - 卡片標題
    sectionTitle: 'text-lg',     // 18px - 區塊標題
  },

  // 富文本編輯器區域
  richText: {
    editor: 'text-base',         // 16px - 編輯器內容
    display: 'text-base',        // 16px - 顯示內容
  }
} as const;

/**
 * 組合樣式類別 - 包含字體大小和其他常用樣式
 */
export const TypographyClasses = {
  // 主要內容樣式
  contentPrimary: `${TypographyStandards.content.primary} text-gray-900 leading-relaxed`,
  contentSecondary: `${TypographyStandards.content.description} text-gray-600 leading-relaxed`,

  // 表格樣式
  tableHeader: `${TypographyStandards.small.tableHeader} font-medium text-gray-500 uppercase tracking-wider`,
  tableCell: `${TypographyStandards.content.tableCell} text-gray-900`,
  tableCellSecondary: `${TypographyStandards.secondary.label} text-gray-600`,

  // 按鈕樣式
  buttonPrimary: `${TypographyStandards.secondary.button} font-medium`,
  buttonSecondary: `${TypographyStandards.secondary.button} font-normal`,

  // 標籤和狀態
  statusBadge: `${TypographyStandards.small.badge} font-medium`,
  hint: `${TypographyStandards.small.hint} text-gray-500`,

  // 標題
  pageTitle: `${TypographyStandards.heading.h1} font-bold text-gray-900`,
  sectionTitle: `${TypographyStandards.heading.h3} font-semibold text-gray-900`,
  cardTitle: `${TypographyStandards.heading.cardTitle} font-medium text-gray-900`,

  // 表單
  formLabel: `${TypographyStandards.secondary.label} font-medium text-gray-700`,
  formInput: `${TypographyStandards.content.input} text-gray-900`,
  formHint: `${TypographyStandards.small.hint} text-gray-500 mt-1`,

  // 導航
  navItem: `${TypographyStandards.secondary.navigation} font-medium`,
  navItemActive: `${TypographyStandards.secondary.navigation} font-semibold`,

  // 富文本
  richTextDisplay: `${TypographyStandards.richText.display} text-gray-700 leading-relaxed prose prose-sm max-w-none`,
} as const;

/**
 * 使用範例：
 *
 * import { TypographyStandards, TypographyClasses } from '../styles/typography';
 *
 * // 基本使用
 * <div className={TypographyStandards.content.primary}>主要內容</div>
 *
 * // 組合樣式
 * <div className={TypographyClasses.contentPrimary}>主要內容</div>
 *
 * // 表格標題
 * <th className={TypographyClasses.tableHeader}>欄位標題</th>
 *
 * // 表格內容
 * <td className={TypographyClasses.tableCell}>表格內容</td>
 */