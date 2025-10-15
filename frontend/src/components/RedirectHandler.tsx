// frontend/src/components/RedirectHandler.tsx

import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * 處理郵件格式 URL 重定向到應用格式
 * 郵件格式: /MyReportAI/?web_type=EIP&cocode=A&daily_no=8855978
 * 應用格式: /MyReportAI/?tab=supervisor&employee=02975&report=8855978
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

    const dailyNo = searchParams.get("daily_no");
    const status = searchParams.get("status");
    const replyid = searchParams.get("replyid");
    const webType = searchParams.get("web_type"); // ✅ 獲取 web_type
    const cocode = searchParams.get("cocode"); // ✅ 獲取 cocode

    if (dailyNo) {
      // 呼叫後端API解析 daily_no 對應的 employee
      const resolveAndRedirect = async () => {
        try {
          const response = await authFetch(
            `/api/supervisor/resolve-report/${dailyNo}`
          );

          if (!response.ok) {
            throw new Error("無法解析日報連結");
          }

          const data = await response.json();
          const employeeId = data.employee_id;

          // 構建新的 URL 參數（包含 employee 和 report）
          const params = new URLSearchParams({
            tab: "supervisor",
            employee: employeeId,
            report: dailyNo,
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
          console.error("解析日報連結失敗:", err);
          setError("無法載入日報，請稍後再試");
          // 3秒後跳轉到首頁
          setTimeout(() => {
            navigate("?tab=supervisor", { replace: true });
          }, 3000);
        }
      };

      resolveAndRedirect();
    } else {
      // 如果沒有 daily_no，導向首頁
      navigate("?tab=supervisor", { replace: true });
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
            <p className="text-gray-600">載入日報中...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default RedirectHandler;
