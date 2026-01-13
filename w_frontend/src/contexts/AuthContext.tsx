// frontend/src/contexts/AuthContext.tsx

import React, {
  createContext,
  useState,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
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

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 在應用程式啟動時驗證 token
  useEffect(() => {
    const verifyAuth = async () => {
      const storedToken = localStorage.getItem("authToken");
      const storedUser = localStorage.getItem("user");

      if (!storedToken || !storedUser) {
        setIsLoading(false);
        return;
      }

      try {
        // 驗證 token 是否仍然有效
        const response = await fetch(buildApiUrl("/api/auth/me"), {
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });

        if (response.ok) {
          // Token 有效，恢復用戶狀態
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
        } else {
          // Token 無效，清除本地儲存
          localStorage.removeItem("authToken");
          localStorage.removeItem("user");
        }
      } catch (error) {
        console.error("Token verification failed:", error);
        localStorage.removeItem("authToken");
        localStorage.removeItem("user");
      } finally {
        setIsLoading(false);
      }
    };

    verifyAuth();
  }, []);

  const login = useCallback((newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem("authToken", newToken);
    localStorage.setItem("user", JSON.stringify(newUser)); // <-- 將 user 物件存入 localStorage
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("authToken");
    localStorage.removeItem("user");

    // 設置手動登出標記，避免自動 SSO
    sessionStorage.setItem("manual_logout", "true");

    // 重新載入到根路徑，讓 ProtectedRoute 處理導航到登入頁
    // 使用根路徑避免 404 錯誤（SPA 不應該直接訪問 /login）
    window.location.replace("/MyReportAI_Weekly/");
  }, []);

  const isAuthenticated = !isLoading && !!token;

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
        // 清除本地儲存的認證資料
        localStorage.removeItem("authToken");
        localStorage.removeItem("user");

        // 檢查是否為 SSO 使用者切換
        const errorData = await response.json().catch(() => ({}));
        if (errorData.detail === "SSO user changed, please re-authenticate") {
          // SSO 使用者已切換，清除狀態並重新載入頁面
          // 不設置 manual_logout 標記，讓登入頁自動觸發 SSO 登入
          setToken(null);
          setUser(null);
          // 使用 replace 導航到登入頁，避免 404
          window.location.replace("/MyReportAI_Weekly/");
        } else {
          // 一般的 session 過期
          logout();
        }
        throw new Error("Session expired");
      }

      return response;
    },
    [token, logout]
  );

  // 在初始化完成前顯示載入畫面
  if (isLoading) {
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
      value={{
        token,
        user,
        login,
        logout,
        isAuthenticated,
        authFetch,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
