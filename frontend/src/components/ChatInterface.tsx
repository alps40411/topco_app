// frontend/src/components/ChatInterface.tsx

import React, { useState, useEffect, useCallback } from "react";
import { User, Crown, MessageCircle, Sparkles, Loader2 } from "lucide-react";
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
  rating?: number; // 評分（如果是審閱留言）
  replies: Comment[];
}

interface AISuggestion {
  type: string;
  title: string;
  content: string;
}

interface ChatInterfaceProps {
  reportId: number;
  reportOwnerId?: number; // 報告擁有者的員工ID
  className?: string;
  reportStatus?: string;
  approvals: SupervisorApprovalInfo[];
  onReviewSubmitted?: () => void;
  onReviewCompleted?: () => void; // 主管評分完成後的回調
  isReadOnly?: boolean; // 新增只讀模式屬性
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  reportId,
  reportOwnerId,
  className = "",
  // reportStatus, // 暫時未使用
  approvals, // Added prop
  onReviewSubmitted,
  onReviewCompleted,
  isReadOnly = false, // 預設為 false
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 審閱相關狀態
  const [selectedRating, setSelectedRating] = useState<number>(3); // 預設評分為「普通」(5分制)
  const [reviewComment, setReviewComment] = useState("");
  const [hasSubmittedReview, setHasSubmittedReview] = useState(false);

  // AI建議相關狀態
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [showAISuggestions, setShowAISuggestions] = useState(false);

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
    if (!authFetch) return;
    try {
      setIsLoading(true);
      const response = await authFetch(`/api/reports/${reportId}/comments`);
      if (response.ok) {
        const commentsData = await response.json();
        setComments(commentsData);
      } else {
        setComments([]);
      }
    } catch (error) {
      console.error("獲取留言失敗:", error);
      toast.error("載入留言失敗");
    } finally {
      setIsLoading(false);
    }
  }, [reportId, authFetch]);

  useEffect(() => {
    if (authFetch) {
      fetchComments();
    }
  }, [fetchComments, authFetch]);

  const handleSubmitMessage = async () => {
    if (!newMessage.trim() || !authFetch) return;
    setIsSubmitting(true);
    try {
      const response = await authFetch(`/api/reports/${reportId}/comments`, {
        method: "POST",
        body: JSON.stringify({ content: newMessage }),
      });
      if (response.ok) {
        setNewMessage("");
        toast.success("留言已送出");
        await fetchComments();
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
    if (!reviewComment.trim()) {
      toast.error("請輸入審閱意見");
      return;
    }
    if (!authFetch) return;
    setIsSubmitting(true);
    try {
      const response = await authFetch(
        `/api/supervisor/reports/${reportId}/review`,
        {
          method: "PUT",
          body: JSON.stringify({
            rating: selectedRating,
            comment: reviewComment.trim(),
          }),
        }
      );
      if (response.ok) {
        toast.success("審閱已提交");
        setHasSubmittedReview(true);
        if (onReviewSubmitted) onReviewSubmitted();
        await fetchComments();
        // 評分完成後跳轉回審閱列表
        if (onReviewCompleted) {
          setTimeout(() => {
            onReviewCompleted();
          }, 1500); // 延遲1.5秒讓用戶看到成功訊息
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitMessage();
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
    // 不關閉 AI 建議，讓用戶可以繼續選擇其他建議
    // setShowAISuggestions(false);
    toast.success(`已套用「${suggestion.title}」建議`);
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

  const ratingOptions = [
    { value: 1, label: "很差" },
    { value: 2, label: "差" },
    { value: 3, label: "普通" },
    { value: 4, label: "好" },
    { value: 5, label: "很好" },
  ];

  const getRatingText = (rating: number) => {
    return ratingOptions.find((r) => r.value === rating)?.label || "未評分";
  };

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
        <div className="bg-white border border-gray-300 rounded p-4 min-h-[120px] flex flex-col">
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
          <div className="text-gray-800 leading-relaxed whitespace-pre-wrap flex-1 mb-3">
            {comment.content}
          </div>
          {comment.rating && comment.rating > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded p-2 mt-auto">
              <div className="text-sm font-medium text-amber-700">
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
    "關於這點，我想補充說明...",
    "我會在下次注意這個問題",
    "謝謝建議，我會改進",
  ];

  // const supervisorSuggestedReplies = [
  //   "工作內容詳實，執行效果良好，請繼續保持。",
  //   "報告內容完整，建議在執行細節上可以更加具體。",
  //   "工作進度符合預期，期待看到更多創新想法。",
  //   "整體表現良好，建議加強時程管控。",
  //   "請在下次日報中提供更多執行細節。",
  //   "表現優秀，值得肯定。",
  //   "請注意品質管控的細節。",
  // ];
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
      {!isReadOnly && (
        <div className="border-t border-gray-200 bg-white rounded-b-lg p-4">
          {user?.is_supervisor &&
            !hasSubmittedReview &&
            user.employee?.id !== reportOwnerId && (
              <div className="mb-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-3 flex items-center">
                    <Crown className="w-4 h-4 mr-2" />
                    主管評分與回饋
                  </h4>
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

                  {/* 建議回復按鈕 - 主管版 */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-blue-700">快速回復建議：</p>
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

                    <div className="flex flex-wrap gap-1.5">
                      {/* AI 建議按鈕 */}
                      {showAISuggestions &&
                        aiSuggestions.map((suggestion, index) => (
                          <button
                            key={`ai-${index}`}
                            onClick={() => handleSelectAISuggestion(suggestion)}
                            className="px-2.5 py-1.5 bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700 text-xs rounded-full hover:from-purple-200 hover:to-blue-200 transition-all duration-200 border border-purple-200 text-left max-w-full break-words whitespace-normal leading-snug"
                          >
                            <span className="inline-flex items-start">
                              <span className="mr-1 flex-shrink-0">✨</span>
                              <span className="flex-1">
                                {suggestion.content}
                              </span>
                            </span>
                          </button>
                        ))}

                      {/* 預設快速回覆按鈕 */}
                      {supervisorSuggestedReplies.map((reply, index) => (
                        <button
                          key={`default-${index}`}
                          onClick={() => setReviewComment(reply)}
                          className="px-2.5 py-1.5 bg-blue-100 text-blue-700 text-xs rounded-full hover:bg-blue-200 transition-colors border border-blue-200 text-left max-w-full break-words whitespace-normal leading-snug"
                        >
                          {reply}
                        </button>
                      ))}
                    </div>

                    {/* 收起AI建議的小按鈕 */}
                    {showAISuggestions && aiSuggestions.length > 0 && (
                      <button
                        onClick={() => setShowAISuggestions(false)}
                        className="mt-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        收起 AI 建議
                      </button>
                    )}
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
                      onClick={handleSubmitReview}
                      disabled={!reviewComment.trim() || isSubmitting}
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      {isSubmitting ? "提交中..." : "提交評分"}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedRating(3); // Reset to default (普通)
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
          {user?.is_supervisor &&
            hasSubmittedReview &&
            user.employee?.id !== reportOwnerId && (
              <div className="mb-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-800">
                    ✅ 您已完成此日報的審閱
                  </p>
                </div>
              </div>
            )}
          {(!user?.is_supervisor ||
            hasSubmittedReview ||
            user.employee?.id === reportOwnerId) && (
            <div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-900 mb-3 flex items-center">
                  <User className="w-4 h-4 mr-2" />
                  {user?.is_supervisor && user.employee?.id !== reportOwnerId
                    ? "追加留言"
                    : "員工回復"}
                </h4>
                <div className="mb-3">
                  <p className="text-xs text-slate-700 mb-2">快速回復建議：</p>
                  <div className="flex flex-wrap gap-2">
                    {(user?.is_supervisor &&
                    hasSubmittedReview &&
                    user.employee?.id !== reportOwnerId
                      ? supervisorSuggestedReplies
                      : suggestedReplies
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
                    user?.is_supervisor && user.employee?.id !== reportOwnerId
                      ? "輸入追加留言..."
                      : "輸入您的回復..."
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
      )}
    </div>
  );
};

export default ChatInterface;
