// frontend/src/components/RedirectHandler.tsx

import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * 處理郵件格式 URL 重定向到應用格式（週報系統）
 * 郵件格式: /?web_type=EIP&cocode=A&weekly_no=136463
 * 應用格式: /?tab=weeklyList&report=136463&employee=...
 */
const RedirectHandler: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { authFetch, isAuthenticated } = useAuth();

  useEffect(() => {
    // 如果尚未認證，等待認證完成
    if (!isAuthenticated) {
      return;
    }

    const weeklyNo = searchParams.get("weekly_no");
    const status = searchParams.get("status");
    const replyid = searchParams.get("replyid");
    const webType = searchParams.get("web_type"); // ✅ 獲取 web_type
    const cocode = searchParams.get("cocode"); // ✅ 獲取 cocode

    if (weeklyNo) {
      // ✅ 週報系統：直接使用 weekly_no 作為 report 參數
      // 不需要 resolve API，因為 weekly_no 就是 report ID
      const resolveAndRedirect = async () => {
        try {
          // ✅ 週報系統：構建新的 URL 參數（只需要 report ID）
          // EmployeeDetailTab 只需要 weekly_no (report ID) 就能載入週報詳情
          const params = new URLSearchParams({
            tab: "weeklyList",
            report: weeklyNo,
          });

          // ✅ 保留 web_type 參數
          if (webType) {
            params.set("web_type", webType);
          }

          // ✅ 保留 cocode 參數
          if (cocode) {
            params.set("cocode", cocode);
          }

          if (status) {
            params.set("status", status);
          }

          if (replyid) {
            params.set("replyid", replyid);
          }

          // 重定向到新格式
          navigate(`?${params.toString()}`, { replace: true });
        } catch (err) {
          console.error("解析週報連結失敗:", err);
          setError("無法載入週報，請稍後再試");
          // 3秒後跳轉到首頁
          setTimeout(() => {
            navigate("?tab=weeklyList", { replace: true });
          }, 3000);
        }
      };

      resolveAndRedirect();
    } else {
      // 如果沒有 weekly_no，導向首頁
      navigate("?tab=weeklyList", { replace: true });
    }
  }, [searchParams, navigate, authFetch, isAuthenticated]);

  // 顯示載入中或錯誤訊息
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        {error ? (
          <>
            <div className="text-red-600 mb-4">
              <svg
                className="w-12 h-12 mx-auto mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-gray-600">{error}</p>
            <p className="text-gray-500 text-sm mt-2">即將返回首頁...</p>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">載入週報中...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default RedirectHandler;
