// frontend/src/components/RedirectHandler.tsx

import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/**
 * 處理郵件格式 URL 重定向到應用格式
 * 郵件格式: /MyReportAI/viewed.aspx?web_type=EIP&cocode={公司別}&daily_no={日報編號}&status=P
 * 應用格式: /MyReportAI/?tab=supervisor&report={日報編號}&status=P
 */
const RedirectHandler: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const dailyNo = searchParams.get("daily_no");
    const status = searchParams.get("status");
    const replyid = searchParams.get("replyid");

    if (dailyNo) {
      // 構建新的 URL 參數
      const params = new URLSearchParams({
        tab: "supervisor",
        report: dailyNo,
      });

      if (status) {
        params.set("status", status);
      }

      if (replyid) {
        params.set("replyid", replyid);
      }

      // 重定向到新格式（從 /viewed.aspx 跳轉到根路徑）
      navigate(`/?${params.toString()}`, { replace: true });
    } else {
      // 如果沒有 daily_no，導向首頁
      navigate("/?tab=supervisor", { replace: true });
    }
  }, [searchParams, navigate]);

  // 顯示載入中
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">載入中...</p>
      </div>
    </div>
  );
};

export default RedirectHandler;
