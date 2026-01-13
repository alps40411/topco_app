// frontend/src/utils/companyLogo.ts

/**
 * 根據公司代碼 (cocode) 獲取對應的公司 logo 路徑
 * @param cocode - 公司代碼 (如 'A', 'J07', 'G02' 等)
 * @returns logo 圖片路徑
 */
export function getCompanyLogo(cocode: string | undefined): string {
  // 預設 logo (如果沒有 cocode 或找不到對應的 logo)
  const defaultLogo = "/MyReportAI_Weekly/top_logoA.jpg";

  if (!cocode) {
    return defaultLogo;
  }

  // 將 cocode 轉換為大寫並去除空白
  const normalizedCocode = cocode.trim().toUpperCase();

  // 根據 cocode 映射到對應的 logo 檔案
  // 規則: top_logo{COCODE}.jpg
  const logoPath = `/MyReportAI_Weekly/top_logo${normalizedCocode}.jpg`;

  return logoPath;
}

/**
 * 根據公司代碼獲取公司名稱
 * @param cocode - 公司代碼
 * @returns 公司名稱
 */
export function getCompanyName(cocode: string | undefined): string {
  if (!cocode) {
    return "崇越科技";
  }

  const normalizedCocode = cocode.trim().toUpperCase();

  // 公司名稱映射表 (可根據實際需求擴充)
  const companyNames: Record<string, string> = {
    J: "LANCASTE",
    C01: "電子學會",
    J09: "群越材料",
    J11: "新越能源",
    J21: "越頂科技",
    J28: "台螢全貿",
    A02: "竹科分公司",
    J30: "安心醫管",
    J29: "崇輝先進",
    "3": "商務學會",
    X: "湛能科技",
    Q: "崇越石英",
    C: "SYT",
    "5": "崇越福委",
    H: "建越科技",
    M: "敏盛科技",
    L01: "ASIA TOP",
    N01: "TOPCO GR",
    "0": "敏盛福委",
    "4": "崇盛投資",
    "8": "崇智投資",
    I: "崇越南科",
    A: "崇越科技",
    K: "冠越科技",
    P: "嘉益能源",
    "2": "建越福委",
    "9": "崇越福委",
    H01: "建越台中",
    R: "崇太能源",
    "001": "生活福委",
    "002": "生技福委",
    "003": "崇越運表協會",
    N02: "ASIA-TH",
    G: "新加坡",
    G02: "檳越科技",
    G01: "越南子公司",
    T02: "興業化學",
    T03: "浦飛芯微",
    T: "上海崇誠",
    T01: "上海崇耀",
    T05: "崇越韩国",
    T04: "崇菱化工",
    Z: "蘇州崇越",
    Z01: "蘇州崇耀",
    S: "宥富科技",
    US1: "TOPCO USA",
    J13: "祥越興業",
    J18: "全越運動",
    J15: "鼎越",
    J19: "名人餐飲",
    J20: "恆映能源",
    A01: "台北分公司",
    J27: "曜越綠電",
    J22: "雲越科技",
    N: "US TOPCO",
    J10: "安永生活",
    G04: "永越先進",
    G03: "新加坡安永",
    B: "崇誠貿易",
    F: "香港崇越",
    L: "康寶生醫",
    U: "彩妍國際",
    W: "威凱科技",
    J01: "晶晨能源",
    J14: "晶越能源",
    J07: "安永生技",
    J12: "仁越貿易",
    J16: "廬醫山",
    J23: "光宇工程",
    J17: "安永樂活",
    J24: "台螢實業",
    J25: "日本峻川",
    J26: "達智電子",
    J06: "日本崇越",
    J08: "晶陽能源",
  };

  return companyNames[normalizedCocode] || "崇越科技";
}
