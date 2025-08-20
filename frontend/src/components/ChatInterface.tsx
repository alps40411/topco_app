// frontend/src/components/ChatInterface.tsx

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, User, Crown, MessageCircle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
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
  user_id: number;
  author?: {
    id: number;
    name: string;
    email: string;
  };
  parent_comment_id?: number;
  rating?: number; // 評分（如果是審核留言）
  replies: Comment[];
}

interface ChatInterfaceProps {
  reportId: number;
  className?: string;
  reportStatus?: string;
  approvals: SupervisorApprovalInfo[]; // Added prop
  onReviewSubmitted?: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  reportId,
  className = "",
  reportStatus,
  approvals, // Added prop
  onReviewSubmitted,
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 審核相關狀態
  const [selectedRating, setSelectedRating] = useState<number>(0);
  const [reviewComment, setReviewComment] = useState("");
  const [hasSubmittedReview, setHasSubmittedReview] = useState(false);

  const { authFetch, user } = useAuth();

  // This effect now correctly determines if the current user has reviewed
  useEffect(() => {
    if (user?.employee?.id && approvals) {
      const myApproval = approvals.find(
        (approval) => approval.supervisor_id === user.employee.id
      );
      // A review is considered submitted if the status is no longer pending.
      setHasSubmittedReview(!!myApproval && myApproval.status !== "pending");
    }
  }, [approvals, user]);

  const fetchComments = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await authFetch(`/api/reports/${reportId}/comments`);
      if (response.ok) {
        const commentsData = await response.json();
        setComments(commentsData);

        // The logic to check for review is now handled by the useEffect above
        // to rely on the more reliable 'approvals' data.
      } else {
        setComments([]);
      }
    } catch (error) {
      console.error("獲取留言失敗:", error);
      toast.error("載入留言失敗");
    } finally {
      setIsLoading(false);
    }
  }, [authFetch, reportId]);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  const handleSubmitMessage = async () => {
    if (!newMessage.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await authFetch(`/api/reports/${reportId}/comments`, {
        method: "POST",
        body: JSON.stringify({
          content: newMessage,
        }),
      });

      if (response.ok) {
        const newComment = await response.json();
        // 直接添加新評論到列表中，避免重新獲取
        setComments((prevComments) => [...prevComments, newComment]);
        setNewMessage("");
        toast.success("留言已送出");
      } else {
        throw new Error("提交留言失敗");
      }
    } catch (error) {
      console.error("提交留言失敗:", error);
      toast.error("提交留言失敗");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReview = async () => {
    if (!selectedRating && !reviewComment.trim()) {
      toast.error("請至少提供評分或留言");
      return;
    }

    // 防止重複提交
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    try {
      // 只調用審核API，讓後端統一處理評論創建
      const response = await authFetch(
        `/api/supervisor/reports/${reportId}/review`,
        {
          method: "PUT",
          body: JSON.stringify({
            rating: selectedRating || null,
            comment: reviewComment.trim() || null,
          }),
        }
      );

      if (response.ok) {
        // 重新獲取評論列表以確保數據一致性
        await fetchComments();

        toast.success("審核已提交");
        setHasSubmittedReview(true);
        setSelectedRating(0);
        setReviewComment("");

        if (onReviewSubmitted) {
          onReviewSubmitted(); // 通知父組件更新報告狀態
        }
      } else {
        const errorData = await response.json();
        // 顯示後端返回的錯誤訊息
        throw new Error(errorData.detail || "提交審核失敗");
      }
    } catch (error) {
      console.error("提交審核失敗:", error);
      toast.error(error instanceof Error ? error.message : "提交審核失敗");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitMessage();
    }
  };

  const formatTime = (timeString: string) => {
    const date = new Date(timeString);
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

  const getRatingText = (rating: number) => {
    const labels = ["很差", "差", "普通", "好", "非常好"];
    return labels[rating - 1] || "普通";
  };

  // 扁平化所有評論（包括回覆）
  const flattenComments = (comments: Comment[]): Comment[] => {
    const result: Comment[] = [];

    const addComment = (comment: Comment) => {
      result.push(comment);
      if (comment.replies && comment.replies.length > 0) {
        comment.replies.forEach(addComment);
      }
    };

    comments.forEach(addComment);
    return result.sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  };

  const renderComment = (comment: Comment) => {
    const isAuthorSupervisor =
      comment.author?.email.includes("@supervisor") || false;

    return (
      <div key={comment.id} className="mb-4">
        {/* 評論框 - 統一大小 */}
        <div className="bg-white border border-gray-300 rounded p-4 min-h-[120px] flex flex-col">
          {/* 頂部信息行 */}
          <div className="flex justify-between items-center mb-3 border-b border-gray-200 pb-2">
            <div className="flex items-center space-x-2">
              <span className="font-medium text-gray-900">
                {comment.author?.name || `用戶 ${comment.user_id}`}
              </span>
              {isAuthorSupervisor && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  主管
                </span>
              )}
            </div>
            <div className="text-right text-sm text-gray-500">
              <div className="font-medium">
                {formatTime(comment.created_at)}
              </div>
            </div>
          </div>

          {/* 評論內容 */}
          <div className="text-gray-800 leading-relaxed whitespace-pre-wrap flex-1 mb-3">
            {comment.content}
          </div>

          {/* 評分信息 - 如果有的話 */}
          {comment.rating && comment.rating > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded p-2 mt-auto">
              <div className="text-sm font-medium text-amber-700">
                評分: {getRatingText(comment.rating)} ({comment.rating}/5)
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
    "關於這點，我想補充說明...",
    "我會在下次注意這個問題",
    "謝謝建議，我會改進",
  ];

  const supervisorSuggestedReplies = [
    "工作內容詳實，執行效果良好，請繼續保持。",
    "報告內容完整，建議在執行細節上可以更加具體。",
    "工作進度符合預期，期待看到更多創新想法。",
    "整體表現良好，建議加強時程管控。",
    "請在下次日報中提供更多執行細節。",
    "表現優秀，值得肯定。",
    "請注意品質管控的細節。",
  ];

  const ratingLabels = ["很差", "差", "普通", "好", "非常好"];

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
      {/* 標題列 */}
      <div className="p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <MessageCircle className="w-5 h-5 text-gray-600" />
          <h3 className="font-medium text-gray-900">回應內容</h3>
          {comments.length > 0 && (
            <span className="text-sm text-gray-500">
              ({comments.length} 則留言)
            </span>
          )}
        </div>
      </div>

      {/* 對話區域 */}
      <div className="p-4 bg-gray-50">
        {comments.length === 0 ? (
          <div className="text-center py-8">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500">尚無任何回應</p>
            <p className="text-sm text-gray-400 mt-1">開始第一則留言吧！</p>
          </div>
        ) : (
          <div>
            {flattenComments(comments).map((comment) => renderComment(comment))}
          </div>
        )}
      </div>

      {/* 輸入區域 */}
      <div className="border-t border-gray-200 bg-white rounded-b-lg p-4">
        {/* 主管審核表單 - 只在未評分時顯示 */}
        {user?.is_supervisor && !hasSubmittedReview && (
          <div className="mb-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-3 flex items-center">
                <Crown className="w-4 h-4 mr-2" />
                主管評分與回饋
              </h4>

              <div className="flex items-center space-x-4 mb-3">
                <span className="text-sm font-medium text-gray-700">評分:</span>

                <select
                  value={selectedRating}
                  onChange={(e) => setSelectedRating(Number(e.target.value))}
                  className="border border-gray-300 rounded px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value={0}>選擇評分</option>
                  <option value={1}>1分 - 很差</option>
                  <option value={2}>2分 - 差</option>
                  <option value={3}>3分 - 普通</option>
                  <option value={4}>4分 - 好</option>
                  <option value={5}>5分 - 非常好</option>
                </select>
              </div>

              {/* 建議回復按鈕 - 主管版 */}
              <div className="mb-3">
                <p className="text-xs text-blue-700 mb-2">快速回復建議：</p>
                <div className="flex flex-wrap gap-2">
                  {supervisorSuggestedReplies.map((reply, index) => (
                    <button
                      key={index}
                      onClick={() => setReviewComment(reply)}
                      className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded hover:bg-blue-200 transition-colors border border-blue-200"
                    >
                      {reply.length > 25
                        ? reply.substring(0, 25) + "..."
                        : reply}
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                placeholder="請輸入您的審核意見..."
                className="w-full p-3 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
                rows={4}
                disabled={isSubmitting}
              />

              <div className="flex space-x-2">
                <button
                  onClick={handleSubmitReview}
                  disabled={
                    selectedRating === 0 ||
                    !reviewComment.trim() ||
                    isSubmitting
                  }
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? "提交中..." : "提交評分"}
                </button>
                <button
                  onClick={() => {
                    setSelectedRating(0);
                    setReviewComment("");
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
        {user?.is_supervisor && hasSubmittedReview && (
          <div className="mb-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-sm text-green-800">✅ 您已完成此日報的評分</p>
            </div>
          </div>
        )}

        {/* 多主管評分統計 */}
        {user?.is_supervisor &&
          (() => {
            const supervisorRatings = comments.filter(
              (comment) =>
                comment.rating && comment.rating > 0 && comment.author
            );

            if (supervisorRatings.length > 1) {
              const averageRating =
                supervisorRatings.reduce(
                  (sum, comment) => sum + (comment.rating || 0),
                  0
                ) / supervisorRatings.length;
              return (
                <div className="mb-4">
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                    <p className="text-sm text-amber-800 font-medium">
                      📊 多主管評分統計:
                      {supervisorRatings.map((rating, index) => (
                        <span key={index} className="ml-1">
                          {rating.author?.name}({rating.rating}分)
                          {index < supervisorRatings.length - 1 ? ", " : ""}
                        </span>
                      ))}
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      平均評分: {averageRating.toFixed(1)}/5
                    </p>
                  </div>
                </div>
              );
            }
            return null;
          })()}

        {/* 員工回復區域 - 統一美觀設計 */}
        {(!user?.is_supervisor ||
          hasSubmittedReview ||
          reportStatus !== "pending") && (
          <div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <h4 className="text-sm font-medium text-slate-900 mb-3 flex items-center">
                <User className="w-4 h-4 mr-2" />
                {user?.is_supervisor ? "追加留言" : "員工回復"}
              </h4>

              {/* 建議回復按鈕 - 員工版或主管追加留言版 */}
              <div className="mb-3">
                <p className="text-xs text-slate-700 mb-2">快速回復建議：</p>
                <div className="flex flex-wrap gap-2">
                  {(user?.is_supervisor && hasSubmittedReview
                    ? supervisorSuggestedReplies
                    : suggestedReplies
                  ).map((reply, index) => (
                    <button
                      key={index}
                      onClick={() => setNewMessage(reply)}
                      className="px-3 py-1 bg-slate-100 text-slate-700 text-sm rounded hover:bg-slate-200 transition-colors border border-slate-200"
                    >
                      {reply.length > 25
                        ? reply.substring(0, 25) + "..."
                        : reply}
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  user?.is_supervisor ? "輸入追加留言..." : "輸入您的回復..."
                }
                className="w-full p-3 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-slate-500 focus:border-transparent mb-3"
                rows={4}
                disabled={isSubmitting}
              />

              <div className="flex space-x-2">
                <button
                  onClick={handleSubmitMessage}
                  disabled={!newMessage.trim() || isSubmitting}
                  className="px-4 py-2 bg-slate-500 text-white rounded hover:bg-slate-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? "提交中..." : "確定送出"}
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
    </div>
  );
};

export default ChatInterface;
