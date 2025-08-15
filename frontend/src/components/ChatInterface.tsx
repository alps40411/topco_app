// frontend/src/components/ChatInterface.tsx

import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Crown, MessageCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

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
  rating?: number;  // 評分（如果是審核留言）
  replies: Comment[];
}

interface ChatInterfaceProps {
  reportId: number;
  className?: string;
  reportStatus?: string;
  onReviewSubmitted?: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  reportId, 
  className = '', 
  reportStatus,
  onReviewSubmitted 
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // 審核相關狀態
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [selectedRating, setSelectedRating] = useState<number>(0);
  const [reviewComment, setReviewComment] = useState('');
  
  const { authFetch, user } = useAuth();

  const fetchComments = async () => {
    try {
      setIsLoading(true);
      const response = await authFetch(`/api/reports/${reportId}/comments`);
      if (response.ok) {
        const commentsData = await response.json();
        setComments(commentsData);
      }
    } catch (error) {
      console.error('獲取留言失敗:', error);
      toast.error('載入留言失敗');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [reportId]);


  const handleSubmitMessage = async () => {
    if (!newMessage.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await authFetch(`/api/reports/${reportId}/comments`, {
        method: 'POST',
        body: JSON.stringify({
          content: newMessage
        })
      });

      if (response.ok) {
        const newComment = await response.json();
        // 直接添加新評論到列表中，避免重新獲取
        setComments(prevComments => [...prevComments, newComment]);
        setNewMessage('');
        toast.success('留言已送出');
      } else {
        throw new Error('提交留言失敗');
      }
    } catch (error) {
      console.error('提交留言失敗:', error);
      toast.error('提交留言失敗');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReview = async () => {
    if (!selectedRating && !reviewComment.trim()) {
      toast.error('請至少提供評分或留言');
      return;
    }

    setIsSubmitting(true);
    try {
      // 提交審核
      // 透過留言API提交審核，包含評分
      const response = await authFetch(`/api/reports/${reportId}/comments`, {
        method: 'POST',
        body: JSON.stringify({
          content: reviewComment.trim() || `評分：${selectedRating} 分`,
          rating: selectedRating || null
        })
      });

      if (response.ok) {
        const newComment = await response.json();
        
        // 同時呼叫審核API來更新報告狀態和評分
        await authFetch(`/api/supervisor/reports/${reportId}/review`, {
          method: 'PUT',
          body: JSON.stringify({
            rating: selectedRating || null,
            comment: reviewComment.trim() || null
          })
        });
        
        // 直接添加新評論到列表中，避免重新獲取
        setComments(prevComments => [...prevComments, newComment]);
        toast.success('審核已提交');
        setShowReviewForm(false);
        setSelectedRating(0);
        setReviewComment('');
        if (onReviewSubmitted) {
          onReviewSubmitted(); // 通知父組件更新報告狀態
        }
      } else {
        throw new Error('提交審核失敗');
      }
    } catch (error) {
      console.error('提交審核失敗:', error);
      toast.error('提交審核失敗');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitMessage();
    }
  };

  const formatTime = (timeString: string) => {
    const date = new Date(timeString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return '剛剛';
    if (diffInMinutes < 60) return `${diffInMinutes}分鐘前`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}小時前`;
    
    return date.toLocaleDateString('zh-TW', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
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
    return result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  };

  const renderComment = (comment: Comment) => {
    const isAuthorSupervisor = comment.author?.email.includes('@supervisor') || false;
    
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
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">主管</span>
              )}
            </div>
            <div className="text-right text-sm text-gray-500">
              <div className="font-medium">{formatTime(comment.created_at)}</div>
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
    "謝謝建議，我會改進"
  ];

  const supervisorSuggestedReplies = [
    "工作內容詳實，執行效果良好，請繼續保持。",
    "報告內容完整，建議在執行細節上可以更加具體。",
    "工作進度符合預期，期待看到更多創新想法。",
    "整體表現良好，建議加強時程管控。",
    "請在下次日報中提供更多執行細節。",
    "表現優秀，值得肯定。",
    "請注意品質管控的細節。"
  ];

  const ratingLabels = ["很差", "差", "普通", "好", "非常好"];

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
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
            <span className="text-sm text-gray-500">({comments.length} 則留言)</span>
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
            {flattenComments(comments).map(comment => renderComment(comment))}
          </div>
        )}
      </div>

      {/* 輸入區域 */}
      <div className="border-t border-gray-200 bg-white rounded-b-lg p-4">

        {/* 主管審核表單 */}
        {user?.is_supervisor && reportStatus === 'pending' && !showReviewForm && (
          <div className="mb-4">
            <button
              onClick={() => setShowReviewForm(true)}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              開始審核
            </button>
          </div>
        )}

        {/* 審核表單 */}
        {showReviewForm && (
          <div className="mb-4">
            <div className="flex items-center space-x-4 mb-3">
              <span className="text-sm font-medium text-gray-700">回應給:</span>
              <select
                value={selectedRating}
                onChange={(e) => setSelectedRating(Number(e.target.value))}
                className="border border-gray-300 rounded px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value={0}>選擇評分</option>
                <option value={1}>很差</option>
                <option value={2}>差</option>
                <option value={3}>普通</option>
                <option value={4}>好</option>
                <option value={5}>非常好</option>
              </select>
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
                disabled={selectedRating === 0 || !reviewComment.trim() || isSubmitting}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                確定送出
              </button>
              <button
                onClick={() => {
                  setShowReviewForm(false);
                  setSelectedRating(0);
                  setReviewComment('');
                }}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
              >
                清除重寫
              </button>
            </div>
          </div>
        )}
        
        {/* 一般留言建議回覆按鈕 */}
        {!showReviewForm && (
          <div className="mb-3">
            <div className="flex flex-wrap gap-2">
              {(user?.is_supervisor ? supervisorSuggestedReplies : suggestedReplies).map((reply, index) => (
                <button
                  key={index}
                  onClick={() => setNewMessage(reply)}
                  className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200 transition-colors"
                >
                  {reply.length > 20 ? reply.substring(0, 20) + '...' : reply}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 一般留言輸入 */}
        {!showReviewForm && (
          <div>
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="輸入您的留言..."
              className="w-full p-3 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
              rows={3}
              disabled={isSubmitting}
            />
            <div className="flex space-x-2">
              <button
                onClick={handleSubmitMessage}
                disabled={!newMessage.trim() || isSubmitting}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                確定送出
              </button>
              <button
                onClick={() => setNewMessage('')}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
              >
                清除重寫
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;