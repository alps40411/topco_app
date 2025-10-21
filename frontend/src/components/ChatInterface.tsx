// frontend/src/components/ChatInterface.tsx

import React, { useState, useEffect, useCallback } from "react";
import {
  User,
  Crown,
  MessageCircle,
  Sparkles,
  Loader2,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import toast from "react-hot-toast";

// Duplicating from EmployeeDetailTab, should be centralized
interface SupervisorApprovalInfo {
  supervisor_id: number;
  supervisor_name: string;
  supervisor_empno: string;
  status: "pending" | "approved";
  approved_at?: string;
  rating?: number;
  feedback?: string;
}

export interface Comment {
  id: number;
  content: string;
  created_at: string;
  user_id: string;
  author?: {
    id: string;
    name: string;
  };
  parent_comment_id?: number;
  rating?: number; // 評分（如果是審閱留言）
  forwarded_to?: string; // 轉寄給誰的姓名列表（逗號分隔）
  replies: Comment[];
}

interface AISuggestion {
  type: string;
  title: string;
  content: string;
}

interface ReplyTarget {
  empno: string;
  empname: string;
  is_author: boolean;
}

interface ChatInterfaceProps {
  reportId: number;
  reportOwnerId?: number; // 報告擁有者的員工ID
  reportOwnerEmpno?: string; // 報告擁有者的員工編號
  reportOwnerName?: string; // 報告擁有者的姓名
  reportAuthor?: { empno: string; empname: string } | null; // ✅ 新增: 已獲取的作者資訊
  className?: string;
  reportStatus?: string;
  approvals: SupervisorApprovalInfo[];
  onReviewSubmitted?: () => void;
  onReviewCompleted?: () => void; // 主管評分完成後的回調
  isReadOnly?: boolean; // 新增只讀模式屬性
  selectedForwardUsers?: string[]; // 選中的轉寄用戶
  onForwardUsersChange?: (users: string[]) => void; // 轉寄用戶變更回調
  urlStatus?: string; // URL 中的 status 參數，'P' 表示顯示確認按鈕
  urlReplyId?: string; // ✅ URL 中的 replyid 參數，用於預設回覆目標
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  reportId,
  reportOwnerId,
  reportOwnerEmpno,
  reportOwnerName,
  reportAuthor, // ✅ 接收作者資訊
  className = "",
  // reportStatus, // 暫時未使用
  approvals, // Added prop
  onReviewSubmitted,
  onReviewCompleted,
  isReadOnly = false, // 預設為 false
  selectedForwardUsers = [],
  onForwardUsersChange,
  urlStatus,
  urlReplyId, // ✅ 接收 replyid 參數
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  // 審閱相關狀態
  const [selectedRating, setSelectedRating] = useState<number>(3); // 預設評分為「普通」(5分制)
  const [reviewComment, setReviewComment] = useState("");
  const [hasSubmittedReview, setHasSubmittedReview] = useState(false);

  // AI建議相關狀態
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [showAISuggestions, setShowAISuggestions] = useState(false);

  // 狀態：控制主管常用回覆是否展開
  const [isSupervisorRepliesExpanded, setIsSupervisorRepliesExpanded] =
    useState(false);

  // 回應目標相關狀態
  const [replyTargets, setReplyTargets] = useState<ReplyTarget[]>([]);
  const [selectedReplyTargets, setSelectedReplyTargets] = useState<string[]>(
    []
  );

  const { authFetch, user } = useAuth();

  // This effect now correctly determines if the current user has reviewed
  useEffect(() => {
    if (user?.employee?.empno && approvals && Array.isArray(approvals)) {
      const myApproval = approvals.find(
        (approval) => approval.supervisor_empno === user.employee.empno
      );
      // A review is considered submitted if the status is no longer pending.
      setHasSubmittedReview(!!myApproval && myApproval.status !== "pending");
    } else {
      setHasSubmittedReview(false);
    }
  }, [approvals, user]);

  // 檢查當前用戶是否為此報告的主管
  const isReportSupervisor =
    user?.employee?.empno && approvals && Array.isArray(approvals)
      ? approvals.some(
          (approval) => approval.supervisor_empno === user.employee.empno
        )
      : false;

  // 檢查當前用戶是否為此報告的作者（使用 empno 比對）
  const isReportAuthor =
    user?.employee?.empno && reportOwnerEmpno
      ? user.employee.empno === reportOwnerEmpno
      : false;

  // ✅ 移除 fetchReportAuthor 函數，直接使用傳入的 reportAuthor

  // 建構回應目標列表
  const buildReplyTargets = useCallback(
    async (commentsData: Comment[]) => {
      const targets: ReplyTarget[] = [];
      const seenEmpnos = new Set<string>();

      // ✅ 使用傳入的作者資訊,無需 API 呼叫
      const authorInfo = reportAuthor;
      const currentUserEmpno = user?.employee?.empno
        ? String(user.employee.empno).padStart(5, "0")
        : null;

      if (authorInfo && authorInfo.empno) {
        // 總是添加日報作者到選項中，即使是作者本人
        // 這樣主管在追加留言時也能選擇回應給作者
        targets.push({
          empno: authorInfo.empno,
          empname: authorInfo.empname,
          is_author: true,
        });
        seenEmpnos.add(authorInfo.empno);
      }

      // 確保至少有當前用戶自己作為選項
      if (
        currentUserEmpno &&
        user?.employee?.empnamec &&
        !seenEmpnos.has(currentUserEmpno)
      ) {
        targets.push({
          empno: currentUserEmpno,
          empname: user.employee.empnamec,
          is_author: false,
        });
        seenEmpnos.add(currentUserEmpno);
      }

      // 2. 從 comments 中提取其他已回應的用戶
      if (Array.isArray(commentsData)) {
        commentsData.forEach((comment) => {
          // 嘗試多種方式來提取工號
          let authorEmpno = comment.author?.id;
          let authorName = comment.author?.name || `用戶 ${comment.user_id}`;

          // 確保工號格式正確（補齊到5位數）
          if (authorEmpno) {
            authorEmpno = String(authorEmpno).padStart(5, "0");
          }

          if (authorEmpno && !seenEmpnos.has(authorEmpno)) {
            targets.push({
              empno: authorEmpno,
              empname: authorName,
              is_author: false,
            });
            seenEmpnos.add(authorEmpno);
          }
        });
      }

      setReplyTargets(targets);

      // ✅ 設定預設選擇：優先根據 urlReplyId 選擇，其次選擇日報作者
      if (targets.length > 0) {
        let defaultSelected: string[] = [];

        // 1. 如果有 urlReplyId，找到對應的 comment，並選擇該 comment 的作者
        if (urlReplyId && commentsData.length > 0) {
          const targetComment = commentsData.find(
            (c) => c.id === parseInt(urlReplyId)
          );
          if (targetComment && targetComment.author?.id) {
            const targetEmpno = String(targetComment.author.id).padStart(5, "0");
            // 確保這個 empno 在 targets 中存在
            const targetInList = targets.find((t) => t.empno === targetEmpno);
            if (targetInList) {
              defaultSelected = [targetEmpno];
              console.log(`✅ 根據 replyid=${urlReplyId} 預設回覆給 ${targetInList.empname} (${targetEmpno})`);
            }
          }
        }

        // 2. 如果沒有從 urlReplyId 找到，則使用原有邏輯（選擇日報作者）
        if (defaultSelected.length === 0) {
          const defaultTarget = targets.find((t) => t.is_author);
          if (defaultTarget) {
            defaultSelected = [defaultTarget.empno];
          } else {
            defaultSelected = [targets[0].empno];
          }
        }

        setSelectedReplyTargets(defaultSelected);
      } else {
        setSelectedReplyTargets([]);
      }
    },
    [reportAuthor, user?.employee?.empno, urlReplyId] // ✅ 新增 urlReplyId 依賴
  );

  const fetchComments = useCallback(async () => {
    if (!authFetch) return;
    try {
      setIsLoading(true);
      const response = await authFetch(`/api/reports/${reportId}/comments`);
      if (response.ok) {
        const responseData = await response.json();
        // 處理 API 返回的資料結構
        let commentsData;
        if (responseData.success && responseData.data) {
          // 後端返回 { success: true, data: [...] } 格式
          commentsData = responseData.data;
        } else if (Array.isArray(responseData)) {
          // 直接返回陣列格式
          commentsData = responseData;
        } else {
          console.warn("Unexpected API response format:", responseData);
          commentsData = [];
        }

        // 確保 commentsData 是陣列
        if (Array.isArray(commentsData)) {
          setComments(commentsData);
          // 建構回應目標列表（異步）
          buildReplyTargets(commentsData);
        } else {
          console.warn("API returned non-array comments data:", commentsData);
          setComments([]);
          buildReplyTargets([]);
        }
      } else {
        setComments([]);
        buildReplyTargets([]);
      }
    } catch (error) {
      console.error("獲取留言失敗:", error);
      toast.error("載入留言失敗");
      setComments([]);
      buildReplyTargets([]);
    } finally {
      setIsLoading(false);
    }
  }, [reportId, authFetch, buildReplyTargets]);

  useEffect(() => {
    if (authFetch) {
      fetchComments();
    }
  }, [fetchComments, authFetch]);

  const handleSubmitMessage = async (useDefaultMessage = false) => {
    const finalMessage = useDefaultMessage ? "瞭解 !" : newMessage.trim();
    if (!finalMessage || !authFetch) return;
    setIsSubmitting(true);
    try {
      // 使用統一的 reviews/submit API，不傳評分表示一般回覆
      const response = await authFetch("/api/reviews/submit", {
        method: "POST",
        body: JSON.stringify({
          daily_no: reportId.toString(),
          reply_memo: finalMessage,
          to_users: selectedReplyTargets.filter(
            (target) =>
              target &&
              target !== String(user?.employee?.empno).padStart(5, "0")
          ), // 過濾掉空值和自己
          forward_users: (selectedForwardUsers || [])
            .filter((user) => user) // 過濾掉空值
            .map((uniqueId) => {
              // 從 uniqueId 提取 empno
              // uniqueId 格式: title_05489_title_0 或 dept_category_dept_duty_05489_0
              const parts = uniqueId.split("_");
              if (parts[0] === "title" && parts.length >= 2) {
                return parts[1]; // title_05489_title_0 -> 05489
              } else if (parts[0] === "dept" && parts.length >= 5) {
                return parts[parts.length - 2]; // dept_..._05489_0 -> 05489
              }
              return uniqueId; // 如果格式不對，直接返回原值
            }),
        }),
      });
      if (response.ok) {
        setNewMessage("");
        toast.success("回覆已送出");
        onForwardUsersChange?.([]); // 清空轉寄選擇
        await fetchComments();

        // ✅ 檢查是否從 EIP 進入，決定跳轉目標
        const urlParams = new URLSearchParams(window.location.search);
        const webType = urlParams.get("web_type");
        if (webType === "EIP") {
          window.location.href = "../TopcoWebCore/InBox";
        } else {
          // ✅ 保留當前選擇的日期
          const dateParam = urlParams.get("date");
          const url = dateParam
            ? `?tab=supervisor&date=${dateParam}`
            : "?tab=supervisor";
          navigate(url);
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || "提交回覆失敗");
      }
    } catch (error) {
      console.error("提交回覆失敗:", error);
      toast.error(error instanceof Error ? error.message : "提交回覆失敗");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReview = async (useDefaultComment = false) => {
    const finalComment = useDefaultComment ? "瞭解 !" : reviewComment.trim();
    if (!finalComment) {
      toast.error("請輸入審閱意見");
      return;
    }
    if (!authFetch) return;
    setIsSubmitting(true);
    try {
      // 使用新的評分回復 API 端點
      const response = await authFetch("/api/reviews/submit", {
        method: "POST",
        body: JSON.stringify({
          daily_no: reportId.toString(),
          score: selectedRating,
          reply_memo: finalComment,
          to_users: selectedReplyTargets.filter(
            (target) =>
              target &&
              target !== String(user?.employee?.empno).padStart(5, "0")
          ), // 過濾掉空值和自己
          forward_users: (selectedForwardUsers || [])
            .filter((user) => user) // 過濾掉空值
            .map((uniqueId) => {
              // 從 uniqueId 提取 empno
              // uniqueId 格式: title_05489_title_0 或 dept_category_dept_duty_05489_0
              const parts = uniqueId.split("_");
              if (parts[0] === "title" && parts.length >= 2) {
                return parts[1]; // title_05489_title_0 -> 05489
              } else if (parts[0] === "dept" && parts.length >= 5) {
                return parts[parts.length - 2]; // dept_..._05489_0 -> 05489
              }
              return uniqueId; // 如果格式不對，直接返回原值
            }),
        }),
      });

      if (response.ok) {
        const result = await response.json();
        let message = "審閱已提交";
        if (selectedForwardUsers.length > 0) {
          message += `，並已轉寄給 ${selectedForwardUsers.length} 位主管`;
        }
        toast.success(message);

        setHasSubmittedReview(true);
        onForwardUsersChange?.([]); // 清空轉寄選擇

        if (onReviewSubmitted) onReviewSubmitted();
        await fetchComments();

        // ✅ 檢查是否從 EIP 進入，決定跳轉目標
        const urlParams = new URLSearchParams(window.location.search);
        const webType = urlParams.get("web_type");
        if (webType === "EIP") {
          window.location.href = "../TopcoWebCore/InBox";
        } else {
          // ✅ 保留當前選擇的日期
          const dateParam = urlParams.get("date");
          const url = dateParam
            ? `?tab=supervisor&date=${dateParam}`
            : "?tab=supervisor";
          navigate(url);
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || "提交審閱失敗");
      }
    } catch (error) {
      console.error("提交審閱失敗:", error);
      toast.error(error instanceof Error ? error.message : "提交審閱失敗");
    } finally {
      setIsSubmitting(false);
    }
  };

  // 確認按鈕處理函數（status=P 時使用）
  const handleAcknowledge = async () => {
    if (!authFetch) return;
    setIsSubmitting(true);
    try {
      const response = await authFetch("/api/reports/acknowledge", {
        method: "POST",
        body: JSON.stringify({
          daily_no: reportId.toString(),
        }),
      });

      if (response.ok) {
        // ✅ 檢查是否從 EIP 進入，決定跳轉目標
        const urlParams = new URLSearchParams(window.location.search);
        const webType = urlParams.get("web_type");
        if (webType === "EIP") {
          window.location.href = "../TopcoWebCore/InBox";
        } else {
          // ✅ 保留當前選擇的日期
          const dateParam = urlParams.get("date");
          const url = dateParam
            ? `?tab=supervisor&date=${dateParam}`
            : "?tab=supervisor";
          navigate(url);
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || "確認失敗");
      }
    } catch (error) {
      console.error("確認失敗:", error);
      toast.error(error instanceof Error ? error.message : "確認失敗");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitMessage(!newMessage.trim());
    }
  };

  const handleGetAISuggestions = async () => {
    if (!authFetch) return;
    setIsLoadingAI(true);
    try {
      const response = await authFetch(
        `/api/supervisor/reports/${reportId}/ai-suggestions`,
        {
          method: "POST",
        }
      );
      if (response.ok) {
        const data = await response.json();
        setAiSuggestions(data.suggestions || []);
        setShowAISuggestions(true);
        toast.success("AI 建議已生成！");
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || "獲取 AI 建議失敗");
      }
    } catch (error: any) {
      console.error("獲取 AI 建議失敗:", error);
      toast.error(error.message || "獲取 AI 建議失敗");
    } finally {
      setIsLoadingAI(false);
    }
  };

  const handleSelectAISuggestion = (suggestion: AISuggestion) => {
    setReviewComment(suggestion.content);
    toast.success(`已套用「${suggestion.title}」建議`);
  };

  const parseTimeString = (timeString: string): Date => {
    if (!timeString) return new Date(0);

    // 處理 YYYYMMDD HH:MM:SS 格式 (如: "20250905 11:35:37")
    if (/^\d{8}\s+\d{2}:\d{2}:\d{2}$/.test(timeString)) {
      const datePart = timeString.substring(0, 8);
      const timePart = timeString.substring(9);
      const year = datePart.substring(0, 4);
      const month = datePart.substring(4, 6);
      const day = datePart.substring(6, 8);

      const date = new Date(`${year}-${month}-${day}T${timePart}`);
      return isNaN(date.getTime()) ? new Date(0) : date;
    }

    // 處理 YYYYMMDD HHMMSS 格式 (如: "20250905 110903")
    if (/^\d{8}\s+\d{6}$/.test(timeString)) {
      const datePart = timeString.substring(0, 8);
      const timePart = timeString.substring(9, 15);
      const year = datePart.substring(0, 4);
      const month = datePart.substring(4, 6);
      const day = datePart.substring(6, 8);
      const hour = timePart.substring(0, 2);
      const minute = timePart.substring(2, 4);
      const second = timePart.substring(4, 6);

      const date = new Date(
        `${year}-${month}-${day}T${hour}:${minute}:${second}`
      );
      return isNaN(date.getTime()) ? new Date(0) : date;
    }

    // 處理 YYYYMMDDHHMMSS 格式 (如: "20250905110903")
    if (/^\d{14}$/.test(timeString)) {
      const year = timeString.substring(0, 4);
      const month = timeString.substring(4, 6);
      const day = timeString.substring(6, 8);
      const hour = timeString.substring(8, 10);
      const minute = timeString.substring(10, 12);
      const second = timeString.substring(12, 14);

      const date = new Date(
        `${year}-${month}-${day}T${hour}:${minute}:${second}`
      );
      return isNaN(date.getTime()) ? new Date(0) : date;
    }

    // 處理標準 ISO 格式
    try {
      const date = new Date(timeString);
      return isNaN(date.getTime()) ? new Date(0) : date;
    } catch {
      return new Date(0);
    }
  };

  const formatTime = (timeString: string) => {
    if (!timeString) return "無時間";

    const date = parseTimeString(timeString);
    if (date.getTime() === 0) return "無效時間";

    const now = new Date();
    const diffInMinutes = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60)
    );
    if (diffInMinutes < 1) return "剛剛";
    if (diffInMinutes < 60) return `${diffInMinutes}分鐘前`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}小時前`;
    return date.toLocaleDateString("zh-TW", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const ratingOptions = [
    { value: 1, label: "很差" },
    { value: 2, label: "差" },
    { value: 3, label: "普通" },
    { value: 4, label: "好" },
    { value: 5, label: "非常好" },
  ];

  const getRatingText = (rating: number) => {
    return ratingOptions.find((r) => r.value === rating)?.label || "未評分";
  };

  const flattenComments = (comments: Comment[]): Comment[] => {
    if (!Array.isArray(comments)) {
      console.warn("comments is not an array:", comments);
      return [];
    }

    const result: Comment[] = [];
    const addComment = (comment: Comment) => {
      result.push(comment);
      if (
        comment.replies &&
        Array.isArray(comment.replies) &&
        comment.replies.length > 0
      ) {
        comment.replies.forEach(addComment);
      }
    };
    comments.forEach(addComment);
    return result.sort((a, b) => {
      const timeA = parseTimeString(a.created_at);
      const timeB = parseTimeString(b.created_at);
      return timeA.getTime() - timeB.getTime();
    });
  };

  const renderComment = (comment: Comment) => {
    // Note: Supervisor detection logic removed as email field is deprecated
    const isAuthorSupervisor = false;
    return (
      <div key={comment.id} className="mb-4">
        <div className="bg-white border border-gray-300 rounded p-4 min-h-[120px] flex flex-col">
          <div className="flex justify-between items-center mb-3 border-b border-gray-200 pb-2">
            <div className="flex items-center space-x-2 flex-wrap">
              <span className="text-sm font-medium text-gray-900">
                {comment.author?.name || `用戶 ${comment.user_id}`}
              </span>
              {isAuthorSupervisor && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  主管
                </span>
              )}
              {comment.forwarded_to && (
                <span className="font-size:14px bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  轉寄給:{" "}
                  {comment.forwarded_to
                    .split(", ")
                    .map((name) => `${name}`)
                    .join(" ")}
                </span>
              )}
            </div>
            <div className="text-right text-base text-gray-500">
              <div className="font-medium">
                {formatTime(comment.created_at)}
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap flex-1 mb-3">
            {comment.content}
          </div>
          {comment.rating && comment.rating > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded p-2 mt-auto">
              <div className="text-base font-medium text-amber-700">
                評分: {getRatingText(comment.rating)}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };
  const suggestedReplies = [
    "好的，我會修改",
    "收到，謝謝主管指導",
    "我會在下次注意這個問題",
    "謝謝建議，我會改進",
    "已瞭解",
  ];

  const supervisorSuggestedReplies = [
    "Good Job !",
    "Go Ahead !",
    "Well Done & Thanks !",
    "內容過於簡單 !",
    "瞭解 !",
  ];
  if (isLoading) {
    return (
      <div
        className={`bg-white rounded-lg border border-gray-200 ${className}`}
      >
        <div className="p-4 text-center text-gray-500">載入對話中...</div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {comments.length > 0 && (
        <>
          <div className="p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
            <div className="flex items-center space-x-2">
              <MessageCircle className="w-5 h-5 text-gray-600" />
              <h3 className="font-medium text-gray-900">回應內容</h3>
              <span className="text-sm text-gray-500">
                ({comments.length} 則留言)
              </span>
            </div>
          </div>
          <div className="p-4 bg-gray-50">
            <div>
              {flattenComments(comments).map((comment) =>
                renderComment(comment)
              )}
            </div>
          </div>
        </>
      )}
      <div className="p-4 bg-gray-50">
        {/* 統一的瞭解!/確認按鈕 */}
        <div className="flex justify-end mt-4">
          <button
            onClick={() => {
              // 只判斷 URL 中的 status 參數
              if (urlStatus === "P") {
                // status=P -> 確認按鈕
                handleAcknowledge();
              } else if (
                isReportSupervisor &&
                !hasSubmittedReview &&
                !isReportAuthor
              ) {
                // 只有主管尚未評分時才用評分功能
                handleSubmitReview(true);
              } else {
                // 所有其他情況（員工回覆、主管已評分後的追加留言等）
                handleSubmitMessage(true);
              }
            }}
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            {isSubmitting ? "送出中..." : urlStatus === "P" ? "確認" : "瞭解 !"}
          </button>
        </div>
      </div>
      {!isReadOnly && (
        <div className="border-t border-gray-200 bg-white rounded-b-lg p-4">
          {isReportSupervisor && !hasSubmittedReview && !isReportAuthor && (
            <div className="mb-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-blue-900 flex items-center">
                    <Crown className="w-4 h-4 mr-2" />
                    主管評分與回饋
                  </h4>
                  {/* 回應目標選擇器 - 放在標題右側 */}
                  {replyTargets.length > 0 && (
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-blue-700">回應給：</span>
                      <select
                        value={
                          selectedReplyTargets.length === replyTargets.length
                            ? "all"
                            : selectedReplyTargets[0] || ""
                        }
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === "all") {
                            setSelectedReplyTargets(
                              replyTargets
                                .map((t) => t.empno)
                                .filter((empno) => empno)
                            );
                          } else if (value) {
                            setSelectedReplyTargets([value]);
                          }
                        }}
                        className="text-xs border border-blue-300 rounded px-2 py-1 bg-white text-blue-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        {replyTargets.map((target) => (
                          <option key={target.empno} value={target.empno}>
                            {target.empname}
                            {/* {target.is_author ? " (作者)" : ""} */}
                          </option>
                        ))}
                        {replyTargets.length > 1 && (
                          <option value="all">全部</option>
                        )}
                      </select>
                    </div>
                  )}
                </div>
                <div className="mb-4">
                  <span className="text-sm font-medium text-gray-700 mr-4">
                    評分:
                  </span>
                  <div
                    className="inline-flex rounded-md shadow-sm"
                    role="group"
                  >
                    {ratingOptions.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setSelectedRating(option.value)}
                        className={`px-4 py-2 text-sm font-medium border transition-colors
                            ${
                              selectedRating === option.value
                                ? "bg-blue-500 text-white border-blue-500 z-10"
                                : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                            }
                            ${option.value === 1 ? "rounded-l-lg" : ""}
                            ${option.value === 5 ? "rounded-r-lg" : ""}
                          `}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 建議回復區塊 */}
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-blue-700">快速回覆建議：</p>
                    <button
                      onClick={handleGetAISuggestions}
                      disabled={isLoadingAI}
                      className="inline-flex items-center px-3 py-1 bg-gradient-to-r from-purple-500 to-blue-500 text-white text-xs rounded-full hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg"
                    >
                      {isLoadingAI ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          生成中...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3 mr-1" />
                          AI 產生建議
                        </>
                      )}
                    </button>
                  </div>

                  {/* AI 建議 (垂直排列, Tag 樣式) */}
                  {showAISuggestions && aiSuggestions.length > 0 && (
                    <div className="flex flex-col items-start gap-2 mb-3">
                      {aiSuggestions.map((suggestion, index) => (
                        <button
                          key={`ai-${index}`}
                          onClick={() => handleSelectAISuggestion(suggestion)}
                          className="px-2.5 py-1.5 bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 text-xs rounded-full hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 text-left max-w-full break-words whitespace-normal leading-snug"
                        >
                          <span className="inline-flex items-start">
                            <span className="mr-1 flex-shrink-0">✨</span>
                            <span className="flex-1">{suggestion.content}</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* 主管常用回覆 (水平展開/收合) - NEW ANIMATION */}
                  <div
                    className="relative flex items-center"
                    style={{ minHeight: "32px" }}
                  >
                    {/* The expanded content, positioned to appear when active */}
                    <div
                      className={`flex items-center transition-all duration-300 ease-in-out ${
                        isSupervisorRepliesExpanded
                          ? "opacity-100 transform scale-100"
                          : "opacity-0 transform scale-95 pointer-events-none"
                      }`}
                    >
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {supervisorSuggestedReplies.map((reply, index) => (
                          <button
                            key={`default-${index}`}
                            onClick={() => setReviewComment(reply)}
                            className="px-2.5 py-1.5 bg-blue-100 text-blue-700 text-xs rounded-full hover:bg-blue-200 transition-colors border border-blue-200 whitespace-nowrap"
                          >
                            {reply}
                          </button>
                        ))}
                      </div>

                      {/* Collapse button */}
                      <button
                        onClick={() => setIsSupervisorRepliesExpanded(false)}
                        className="ml-2 flex flex-shrink-0 items-center px-2.5 py-1.5 bg-gray-100 text-gray-700 text-xs rounded-full hover:bg-gray-200 transition-colors border border-gray-200 whitespace-nowrap"
                      >
                        <ChevronLeft className="w-4 h-4" />
                        <span className="hidden sm:inline ml-1">收起</span>
                      </button>
                    </div>

                    {/* The "Expand" button, which disappears when content is shown */}
                    <button
                      onClick={() => setIsSupervisorRepliesExpanded(true)}
                      className={`absolute top-0 left-0 flex items-center px-2.5 py-1.5 bg-blue-100 text-blue-700 text-xs rounded-full hover:bg-blue-200 transition-all duration-300 ease-in-out border border-blue-200 ${
                        isSupervisorRepliesExpanded
                          ? "opacity-0 scale-95 pointer-events-none"
                          : "opacity-100 scale-100"
                      }`}
                      aria-expanded={isSupervisorRepliesExpanded}
                    >
                      <span>常用回覆</span>
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </button>
                  </div>
                </div>

                <textarea
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  placeholder="請輸入您的審閱意見..."
                  className="w-full p-3 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
                  rows={4}
                  disabled={isSubmitting}
                />

                <div className="flex space-x-2">
                  <button
                    onClick={() => handleSubmitReview(false)}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSubmitting ? "提交中..." : "提交評分"}
                  </button>
                  <button
                    onClick={() => {
                      setSelectedRating(3); // Reset to default (普通)
                      setReviewComment("");
                      onForwardUsersChange?.([]); // 清空轉寄選擇
                      // 重置回應目標選擇到預設值
                      if (replyTargets.length > 0) {
                        const defaultTarget = replyTargets.find(
                          (t) => t.is_author
                        );
                        if (defaultTarget) {
                          setSelectedReplyTargets([defaultTarget.empno]);
                        } else {
                          setSelectedReplyTargets([replyTargets[0].empno]);
                        }
                      }
                    }}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:bg-gray-300 transition-colors"
                  >
                    清除重寫
                  </button>
                </div>
              </div>
            </div>
          )}
          {/* 已評分提示 */}
          {isReportSupervisor && hasSubmittedReview && !isReportAuthor && (
            <div className="mb-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <p className="text-sm text-green-800">
                  ✅ 您已完成此日報的審閱
                </p>
              </div>
            </div>
          )}
          {(!isReportSupervisor || hasSubmittedReview || isReportAuthor) && (
            <div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-slate-900 flex items-center">
                    <User className="w-4 h-4 mr-2" />
                    {/* 作者本人顯示「員工回覆」，其他所有人（主管已評分、第三方用戶）都顯示「追加留言」 */}
                    {isReportAuthor ? "員工回覆" : "追加留言"}
                  </h4>
                  {/* 回應目標選擇器 - 放在標題右側 */}
                  {replyTargets.length > 0 && (
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-slate-700">回應給：</span>
                      <select
                        value={
                          selectedReplyTargets.length === replyTargets.length
                            ? "all"
                            : selectedReplyTargets[0] || ""
                        }
                        onChange={(e) => {
                          const value = e.target.value;
                          if (value === "all") {
                            setSelectedReplyTargets(
                              replyTargets
                                .map((t) => t.empno)
                                .filter((empno) => empno)
                            );
                          } else if (value) {
                            setSelectedReplyTargets([value]);
                          }
                        }}
                        className="text-xs border border-slate-300 rounded px-2 py-1 bg-white text-slate-700 focus:ring-2 focus:ring-slate-500 focus:border-transparent"
                      >
                        {replyTargets.map((target) => (
                          <option key={target.empno} value={target.empno}>
                            {target.empname}
                            {/* {target.is_author ? " (作者)" : ""} */}
                          </option>
                        ))}
                        {replyTargets.length > 1 && (
                          <option value="all">全部</option>
                        )}
                      </select>
                    </div>
                  )}
                </div>
                <div className="mb-3">
                  <p className="text-xs text-slate-700 mb-2">快速回覆建議：</p>
                  <div className="flex flex-wrap gap-2">
                    {/* 只有作者本人顯示員工回覆建議，其他所有人都顯示主管回覆建議 */}
                    {(isReportAuthor
                      ? suggestedReplies
                      : supervisorSuggestedReplies
                    ).map((reply, index) => (
                      <button
                        key={index}
                        onClick={() => setNewMessage(reply)}
                        className="px-3 py-1 bg-slate-100 text-slate-700 text-sm rounded hover:bg-slate-200 transition-colors border border-slate-200"
                      >
                        {reply}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    isReportAuthor ? "輸入您的回覆..." : "輸入追加留言..."
                  }
                  className="w-full p-3 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-slate-500 focus:border-transparent mb-3"
                  rows={4}
                  disabled={isSubmitting}
                />
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleSubmitMessage()}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-slate-500 text-white rounded hover:bg-slate-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSubmitting ? "提交中..." : "確認送出"}
                  </button>
                  <button
                    onClick={() => setNewMessage("")}
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:bg-gray-300 transition-colors"
                  >
                    清除重寫
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
