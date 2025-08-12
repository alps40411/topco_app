import React, { useState, useRef, useEffect } from 'react';
import { Wand2, Save, Search, Upload, Plus } from 'lucide-react';
import type { WorkRecord } from '../App';

interface AIBraftTabProps {
  aiDraft: string;
  setAiDraft: (draft: string) => void;
  workRecords: WorkRecord[];
  highlightedCategories: string[];
  onCategoryHighlight: (category: string) => void;
}

const AIBraftTab: React.FC<AIBraftTabProps> = ({
  aiDraft,
  setAiDraft,
  workRecords,
  highlightedCategories,
  onCategoryHighlight
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  const formatMarkdownToHtml = (text: string) => {
    return text
      .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mb-4 text-gray-900">$1</h1>')
      .replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mb-3 mt-6 text-gray-800">$1</h2>')
      .replace(/^### (.*$)/gm, '<h3 class="text-lg font-medium mb-2 mt-4 text-gray-700">$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
      .replace(/【(.*?)】/g, (match, category) => {
        const isHighlighted = highlightedCategories.includes(category);
        return `<span class="inline-flex items-center px-2 py-1 text-xs font-medium ${isHighlighted ? 'bg-blue-200 text-blue-900' : 'bg-gray-200 text-gray-800'} rounded-md mr-1 cursor-pointer hover:bg-gray-300" data-category="${category}">【${category}】</span>`;
      })
      .replace(/\n\n/g, '</p><p class="mb-4 text-gray-700 leading-relaxed">')
      .replace(/\n/g, '<br>');
  };

  const highlightSearchTerm = (text: string) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
  };

  const scrollToCategory = (category: string) => {
    if (editorRef.current) {
      const categoryElement = editorRef.current.querySelector(`[data-category="${category}"]`);
      if (categoryElement) {
        categoryElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  const getFilteredRecords = () => {
    let filtered = workRecords;
    
    if (searchTerm) {
      filtered = filtered.filter(record => 
        record.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
        record.project.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // 如果有高亮的分類，將對應的記錄排序到最上方
    if (highlightedCategories.length > 0) {
      const highlighted = filtered.filter(record => highlightedCategories.includes(record.project));
      const others = filtered.filter(record => !highlightedCategories.includes(record.project));
      return [...highlighted, ...others];
    }
    
    return filtered;
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-TW', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTodayRecords = () => {
    const today = new Date().toISOString().split('T')[0];
    return workRecords.filter(record => 
      record.createdAt.split('T')[0] === today
    );
  };

  const handleReferenceClick = (category: string) => {
    onCategoryHighlight(category);
    scrollToCategory(category);
  };

  useEffect(() => {
    // 為草稿中的分類標籤添加點擊事件
    const handleCategoryClick = (event: Event) => {
      const target = event.target as HTMLElement;
      if (target.dataset.category) {
        onCategoryHighlight(target.dataset.category);
      }
    };

    if (editorRef.current) {
      editorRef.current.addEventListener('click', handleCategoryClick);
      return () => {
        if (editorRef.current) {
          editorRef.current.removeEventListener('click', handleCategoryClick);
        }
      };
    }
  }, [aiDraft, highlightedCategories]);

  return (
    <div className="flex gap-6 p-6">
      {/* Left Panel - Editor */}
      <div className="w-2/3">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {/* Editor Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <h3 className="text-lg font-medium text-gray-900">AI工作報告草稿</h3>
          <button className="inline-flex items-center px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
            <Upload className="w-4 h-4 mr-2" />
            上傳
          </button>
        </div>

        {/* Editor Content */}
        <div className="p-6">
          <textarea
            ref={editorRef}
            className="w-full min-h-[600px] p-4 border-0 resize-none focus:outline-none text-gray-700 leading-relaxed"
            value={aiDraft}
            onChange={(e) => {
              setAiDraft(e.target.value);
            }}
            placeholder="開始編寫您的工作報告..."
          />
        </div>
        </div>
      </div>

      {/* Right Panel - Search and References */}
      <div className="w-1/3">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜尋今日筆記..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            共 {getTodayRecords().length} 筆今日筆記
          </h3>
          
          <div className="space-y-3">
            {getFilteredRecords().map((record) => (
              <div 
                key={record.id} 
                className={`p-3 rounded-lg shadow-sm border cursor-pointer transition-all hover:shadow-md ${
                  highlightedCategories.includes(record.project)
                    ? 'bg-blue-50 border-blue-200 shadow-md'
                    : 'bg-white hover:shadow-md'
                }`}
                onClick={() => handleReferenceClick(record.project)}
              >
                <div className="flex items-center space-x-2 mb-2">
                  <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-md ${
                    record.project === 'AI日誌報表統規劃' ? 'bg-blue-100 text-blue-800' :
                    record.project === '專案計畫' ? 'bg-purple-100 text-purple-800' :
                    record.project === '目標設定' ? 'bg-red-100 text-red-800' :
                    record.project === '週計畫制定' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {record.project}
                  </span>
                  <span className="text-xs text-gray-500">
                    <Plus className="w-3 h-3" />
                  </span>
                </div>
                <p className="text-sm text-gray-700 line-clamp-3">
                  {record.content}
                </p>
                <p className="text-xs text-gray-500 mt-2">{formatTime(record.createdAt)}</p>
                
                {/* 檔案附件指示 */}
                {record.files && record.files.length > 0 && (
                  <div className="mt-2 flex items-center text-xs text-gray-500">
                    <span>{record.files.length} 個附件</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
};

export default AIBraftTab;