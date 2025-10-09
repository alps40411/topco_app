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

interface WritingStatus {
  allowed: boolean;
  message: string;
  current_date: string;
  current_time: string;
  next_available_time: string;
  has_other_writable_dates?: boolean;
}

interface AuthContextType {
  token: string | null;
  user: User | null; // <-- 新增 user 狀態
  login: (token: string, user: User) => void; // <-- login 函式現在接收 user 物件
  logout: () => void;
  isAuthenticated: boolean;
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
  hasSubordinates: boolean; // ✅ 新增
  isCheckingSubordinates: boolean; // ✅ 新增
  writingStatus: WritingStatus | null; // ✅ 新增全域寫入狀態
  refreshWritingStatus: (docDate?: string) => Promise<void>; // ✅ 新增刷新函數
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true); //  замість isInitialized
  const [hasSubordinates, setHasSubordinates] = useState(false);
  const [isCheckingSubordinates, setIsCheckingSubordinates] = useState(true);
  const [writingStatus, setWritingStatus] = useState<WritingStatus | null>(
    null
  ); // ✅ 新增全域寫入狀態

  // 在應用程式啟動時驗證 token
  useEffect(() => {
    const verifyAuth = async () => {
      const storedToken = localStorage.getItem("authToken");

      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(buildApiUrl("/api/users/profile"), {
          headers: { Authorization: `Bearer ${storedToken}` },
        });

        if (response.ok) {
          const userData = await response.json();
          // 使用從後端獲取的最新數據
          login(storedToken, userData.data);
        } else {
          // Token 無效或過期
          logout();
        }
      } catch (error) {
        console.error("驗證失敗:", error);
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    verifyAuth();
    // Eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkSubordinates = useCallback(async () => {
    if (!token) return;

    setIsCheckingSubordinates(true);
    try {
      const response = await fetch(
        buildApiUrl("/api/users/has-subordinates"),
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setHasSubordinates(data.has_subordinates);
      }
    } catch (error) {
      setHasSubordinates(false);
    } finally {
      setIsCheckingSubordinates(false);
    }
  }, [token]);

  // ✅ 刷新寫入狀態的函數（改用 dates/range）
  const refreshWritingStatus = useCallback(
    async (docDate?: string) => {
      if (!token || !user?.employee) return;

      try {
        const response = await fetch(buildApiUrl("/api/dates/range"), {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();

          // 從 dates/range 的返回數據構建 WritingStatus
          const status: WritingStatus = {
            allowed: data.allowed,
            message: data.message,
            current_date: data.current_report_date || "",
            current_time: data.current_time || "",
            next_available_time: "", // 不再需要此欄位
            has_other_writable_dates: data.has_other_writable_dates,
          };

          setWritingStatus(status);
        }
      } catch (error) {}
    },
    [token, user?.employee]
  );

  // ✅ 只在登入後檢查一次下屬關係和寫入狀態
  useEffect(() => {
    if (token && user) {
      checkSubordinates();
      refreshWritingStatus(); // ✅ 載入初始寫入狀態
    } else {
      setHasSubordinates(false);
      setIsCheckingSubordinates(false);
      setWritingStatus(null);
    }
  }, [token, user, checkSubordinates, refreshWritingStatus]);

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

    // 強制重新加載頁面確保完全清除狀態
    window.location.href = "/MyReportAI/login";
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
        logout();
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
        hasSubordinates,
        isCheckingSubordinates,
        writingStatus, // ✅ 提供全域寫入狀態
        refreshWritingStatus, // ✅ 提供刷新函數
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
