// frontend/src/utils/companyLogo.ts

/**
 * 根據公司代碼 (cocode) 獲取對應的公司 logo 路徑
 * @param cocode - 公司代碼 (如 'A', 'J07', 'G02' 等)
 * @returns logo 圖片路徑
 */
export function getCompanyLogo(cocode: string | undefined): string {
  // 預設 logo (如果沒有 cocode 或找不到對應的 logo)
  const defaultLogo = '/MyReportAI/top_logoA.jpg';

  if (!cocode) {
    return defaultLogo;
  }

  // 將 cocode 轉換為大寫並去除空白
  const normalizedCocode = cocode.trim().toUpperCase();

  // 根據 cocode 映射到對應的 logo 檔案
  // 規則: top_logo{COCODE}.jpg
  const logoPath = `/MyReportAI/top_logo${normalizedCocode}.jpg`;

  return logoPath;
}

/**
 * 根據公司代碼獲取公司名稱
 * @param cocode - 公司代碼
 * @returns 公司名稱
 */
export function getCompanyName(cocode: string | undefined): string {
  if (!cocode) {
    return '崇越科技';
  }

  const normalizedCocode = cocode.trim().toUpperCase();

  // 公司名稱映射表 (可根據實際需求擴充)
  const companyNames: Record<string, string> = {
    'A': '崇越科技',
    '003': '崇越科技',
    'J': '崇越電通',
    'J01': '崇越電通',
    'J06': '崇越電通',
    'J07': '崇越電通',
    'J08': '崇越電通',
    'J09': '崇越電通',
    'J10': '崇越電通',
    'J11': '崇越電通',
    'J12': '崇越電通',
    'J13': '崇越電通',
    'J14': '崇越電通',
    'J15': '崇越電通',
    'J16': '崇越電通',
    'J17': '崇越電通',
    'J18': '崇越電通',
    'J19': '崇越電通',
    'J21': '崇越電通',
    'J22': '崇越電通',
    'J23': '崇越電通',
    'J25': '崇越電通',
    'J27': '崇越電通',
    'G': '崇越集團',
    'G02': '崇越集團',
    'G03': '崇越集團',
    'G04': '崇越集團',
    'H': '崇越貿易',
    'H01': '崇越貿易',
    'T': '崇越通商',
    'T01': '崇越通商',
    'T02': '崇越通商',
    'C': '崇越',
    'E': '崇越',
    'K': '崇越',
    'L': '崇越',
    'L01': '崇越',
    'M': '崇越',
    'N': '崇越',
    'N01': '崇越',
    'P': '崇越',
    'R': '崇越',
    'S': '崇越',
    'U': '崇越',
    'US1': '崇越',
    'W': '崇越',
    'X': '崇越',
    'Z': '崇越',
    'Z01': '崇越',
    'A01': '崇越科技',
    '4': '崇越',
    '8': '崇越',
  };

  return companyNames[normalizedCocode] || '崇越科技';
}
