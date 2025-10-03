// frontend/src/components/LoginPage.tsx

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { buildApiUrl } from "../config/api";
import { clearDateCache } from "./DateSelector";

const LoginPage: React.FC = () => {
  const [empno, setEmpno] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingSSO, setIsCheckingSSO] = useState(true); // 新增：正在檢查 SSO 狀態
  const { login } = useAuth();
  const navigate = useNavigate();

  // 檢查是否自動啟用 SSO 登入
  React.useEffect(() => {
    const checkSSO = async () => {
      // 檢查是否是手動登出（避免自動重新登入）
      const wasManualLogout = sessionStorage.getItem("manual_logout");
      if (wasManualLogout) {
        sessionStorage.removeItem("manual_logout");
        setIsCheckingSSO(false);
        return;
      }

      try {
        // 清除日期快取，確保獲取新使用者的日期資料
        clearDateCache();

        // 嘗試調用 SSO 登入端點看是否有有效的 SSO headers
        const response = await fetch(buildApiUrl("/api/auth/sso"), {
          method: "POST",
        });

        if (response.ok) {
          const data = await response.json();

          login(data.token.access_token, data.user);
          // 使用完整路徑跳轉
          window.location.href = "/MyReportAI/?tab=supervisor";
        } else {
          // SSO 失敗，顯示傳統登入界面
          setIsCheckingSSO(false);
        }
      } catch (error) {
        // SSO 不可用，使用傳統登入

        setIsCheckingSSO(false);
      }
    };

    checkSSO();
  }, [login, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", empno);
      formData.append("password", "dummy"); // 暫時使用固定密碼，後端不驗證

      const response = await fetch(buildApiUrl("/api/auth/token"), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("登入失敗，請檢查您的員工編號。");
      }

      const data = await response.json();
      login(data.token.access_token, data.user);
      // 使用完整路徑跳轉
      window.location.href = "/MyReportAI/?tab=supervisor";
    } catch (err: any) {
      setError(err.message || "發生未知錯誤");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSSOLogin = async () => {
    setError("");
    setIsLoading(true);

    try {
      // 清除日期快取，確保獲取新使用者的日期資料
      clearDateCache();

      const response = await fetch(buildApiUrl("/api/auth/sso"), {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("SSO 登入失敗，請使用傳統登入方式。");
      }

      const data = await response.json();
      login(data.token.access_token, data.user);
      // 使用完整路徑跳轉
      window.location.href = "/MyReportAI/?tab=supervisor";
    } catch (err: any) {
      setError(err.message || "SSO 登入失敗");
    } finally {
      setIsLoading(false);
    }
  };

  // 如果正在檢查 SSO，顯示 loading 畫面
  if (isCheckingSSO) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="w-full max-w-md p-8 pt-10 space-y-6 bg-white rounded-2xl shadow-lg">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">TSC</span>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">
              登入 TSC 業務日誌
            </h2>
            <p className="mt-1 text-sm text-gray-500">崇越科技</p>
          </div>

          {/* Loading 動畫 */}
          <div className="flex flex-col items-center justify-center py-8">
            <div className="w-12 h-12 border-4 border-green-200 border-t-green-600 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">正在驗證登入...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 pt-10 space-y-6 bg-white rounded-2xl shadow-lg">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <div className="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">TSC</span>
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            登入 TSC 業務日誌
          </h2>
          <p className="mt-1 text-sm text-gray-500">崇越科技</p>
        </div>

        {/* SSO 登入按鈕 */}
        <div className="space-y-4">
          <button
            onClick={handleSSOLogin}
            disabled={isLoading}
            className="w-full flex justify-center items-center px-4 py-3 font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:bg-green-300 transition-colors"
          >
            <LogIn className="w-4 h-4 mr-2" />
            {isLoading ? "登入中..." : "SSO 單一登入"}
          </button>

          {/* 分隔線 */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">或</span>
            </div>
          </div>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              員工編號
            </label>
            <input
              type="text"
              value={empno}
              onChange={(e) => setEmpno(e.target.value)}
              placeholder="請輸入您的員工編號"
              required
              className="w-full px-3 py-2 mt-1 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          {error && <p className="text-sm text-center text-red-600">{error}</p>}
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center items-center px-4 py-3 font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
            >
              <LogIn className="w-4 h-4 mr-2" />
              {isLoading ? "登入中..." : "手動登入"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
export default LoginPage;
