// frontend/src/contexts/AuthContext.tsx

import React, {
  createContext,
  useState,
  useContext,
  ReactNode,
  useCallback,
  useEffect,
} from "react";
import type { User } from "../App"; // 我們將從 App.tsx 引入統一的 User 型別
import { buildApiUrl } from "../config/api";

interface AuthContextType {
  token: string | null;
  user: User | null; // <-- 新增 user 狀態
  login: (token: string, user: User) => void; // <-- login 函式現在接收 user 物件
  logout: () => void;
  isAuthenticated: boolean;
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // 在組件掛載時從 localStorage 讀取認證資訊
  useEffect(() => {
    const storedToken = localStorage.getItem("authToken");
    const storedUser = localStorage.getItem("user");

    if (storedToken) {
      setToken(storedToken);
    }

    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
      } catch (e) {
        console.error("❌ AuthContext - 解析 user 失敗:", e);
        localStorage.removeItem("user");
      }
    }

    setIsInitialized(true);
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("authToken", newToken);
    localStorage.setItem("user", JSON.stringify(newUser)); // <-- 將 user 物件存入 localStorage
  };

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("authToken");
    localStorage.removeItem("user");

    // 設置手動登出標記，避免自動 SSO
    sessionStorage.setItem("manual_logout", "true");

    // 強制重新加載頁面確保完全清除狀態
    window.location.href = "/MyReportAI/login";
  }, []);

  const isAuthenticated = isInitialized && !!token;

  // 添加調試信息

  const authFetch = useCallback(
    async (url: string, options: RequestInit = {}) => {
      const newHeaders = new Headers(options.headers);
      newHeaders.set("Authorization", `Bearer ${token}`);

      if (!(options.body instanceof FormData)) {
        newHeaders.set("Content-Type", "application/json");
      }

      const fullUrl = buildApiUrl(url);
      const response = await fetch(fullUrl, {
        ...options,
        headers: newHeaders,
      });

      if (response.status === 401) {
        logout();
        throw new Error("Session expired");
      }

      return response;
    },
    [token, logout]
  );

  // 在初始化完成前顯示載入畫面
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">載入中...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{ token, user, login, logout, isAuthenticated, authFetch }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
