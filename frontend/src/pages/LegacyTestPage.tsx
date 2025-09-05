// frontend/src/pages/LegacyTestPage.tsx
import React, { useState } from 'react';
import { LegacyApi, type DraftSaveRequest, type ReportSubmitRequest } from '../services/legacyApi';

const LegacyTestPage: React.FC = () => {
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [empno, setEmpno] = useState('03252');
  const [docDate, setDocDate] = useState(() => LegacyApi.formatDateForApi(new Date()));
  const [dailyNo, setDailyNo] = useState<string>('');

  const addResult = (key: string, data: any) => {
    setResults(prev => ({ ...prev, [key]: data }));
  };

  const handleTest = async (testName: string, testFn: () => Promise<any>) => {
    setLoading(testName);
    try {
      const result = await testFn();
      addResult(testName, result);
      console.log(`✅ ${testName} 成功:`, result);
    } catch (error) {
      console.error(`❌ ${testName} 失敗:`, error);
      addResult(testName, { error: error instanceof Error ? error.message : String(error) });
    } finally {
      setLoading(null);
    }
  };

  // 測試函數們
  const testGetNextDailyNo = () => handleTest('獲取新日報編號', async () => {
    const result = await LegacyApi.getNextDailyNo();
    setDailyNo(result.daily_no);
    return result;
  });

  const testGetWorkPlans = () => handleTest('獲取工作計畫', () => 
    LegacyApi.getWorkPlans(empno)
  );

  const testGetCompanies = () => handleTest('獲取公司列表', () => 
    LegacyApi.getCompanies()
  );

  const testGetDailyReports = () => handleTest('獲取日報列表', () => 
    LegacyApi.getDailyReports({ empno, doc_date: docDate })
  );

  const testSaveDraft = () => {
    if (!dailyNo) {
      alert('請先獲取日報編號');
      return;
    }

    const draftData: DraftSaveRequest = {
      daily_no: dailyNo,
      empno: empno,
      cocode: 'A',
      doc_date: docDate,
      draft_type: 'TEMP',
      draft_content: {
        title: '測試日報暫存',
        work_items: [
          {
            planno: 'P001',
            sopno: 'S001',
            sop_code: '系統開發',
            itemdesc1: '進行舊資料庫串接測試',
            exetime: 120,
            memo: '完成API開發和測試'
          }
        ],
        notes: '這是一個測試暫存'
      }
    };

    handleTest('保存暫存', () => LegacyApi.saveDraft(draftData));
  };

  const testGetDrafts = () => handleTest('獲取暫存資料', () => 
    LegacyApi.getDrafts(empno, 'TEMP')
  );

  const testSubmitReport = () => {
    if (!dailyNo) {
      alert('請先獲取日報編號');
      return;
    }

    const submitData: ReportSubmitRequest = {
      daily_no: dailyNo,
      empno: empno,
      cocode: 'A',
      deptno: '00001',
      doc_date: docDate,
      leader: '00001',
      g_deptno: 'G001',
      empnamec: '測試員工',
      deptnamec: '資訊部',
      sop_desc_c: '系統開發測試',
      word_count: 50,
      work_items: [
        {
          planno: 'P001',
          sopno: 'S001',
          sop_code: '系統開發',
          itemdesc1: '舊資料庫串接開發',
          exetime: 240,
          memo: '完成完整的API開發，包含暫存、AI草稿和正式提交功能',
          pps_servecocode: 'A',
          pps_empno: empno,
          pps_cocode: 'A',
          pps_deptno: '00001',
          pps_empnamec: '測試員工'
        }
      ]
    };

    handleTest('提交日報', () => LegacyApi.submitReport(submitData));
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">舊資料庫串接測試頁面</h1>
      
      {/* 測試參數設定 */}
      <div className="bg-gray-100 p-4 rounded-lg mb-6">
        <h2 className="text-lg font-semibold mb-4">測試參數</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">員工編號:</label>
            <input
              type="text"
              value={empno}
              onChange={(e) => setEmpno(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">日期 (YYYYMMDD):</label>
            <input
              type="text"
              value={docDate}
              onChange={(e) => setDocDate(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">日報編號:</label>
            <input
              type="text"
              value={dailyNo}
              onChange={(e) => setDailyNo(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              placeholder="點擊獲取新編號"
            />
          </div>
        </div>
      </div>

      {/* 測試按鈕 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <button
          onClick={testGetNextDailyNo}
          disabled={loading === '獲取新日報編號'}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading === '獲取新日報編號' ? '執行中...' : '獲取新日報編號'}
        </button>
        
        <button
          onClick={testGetWorkPlans}
          disabled={loading === '獲取工作計畫'}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
        >
          {loading === '獲取工作計畫' ? '執行中...' : '獲取工作計畫'}
        </button>
        
        <button
          onClick={testGetCompanies}
          disabled={loading === '獲取公司列表'}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
        >
          {loading === '獲取公司列表' ? '執行中...' : '獲取公司列表'}
        </button>
        
        <button
          onClick={testGetDailyReports}
          disabled={loading === '獲取日報列表'}
          className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50"
        >
          {loading === '獲取日報列表' ? '執行中...' : '獲取日報列表'}
        </button>
        
        <button
          onClick={testSaveDraft}
          disabled={loading === '保存暫存'}
          className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50"
        >
          {loading === '保存暫存' ? '執行中...' : '保存暫存'}
        </button>
        
        <button
          onClick={testGetDrafts}
          disabled={loading === '獲取暫存資料'}
          className="px-4 py-2 bg-teal-500 text-white rounded hover:bg-teal-600 disabled:opacity-50"
        >
          {loading === '獲取暫存資料' ? '執行中...' : '獲取暫存資料'}
        </button>
        
        <button
          onClick={testSubmitReport}
          disabled={loading === '提交日報'}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
        >
          {loading === '提交日報' ? '執行中...' : '提交日報'}
        </button>
        
        <button
          onClick={() => setResults({})}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          清除結果
        </button>
      </div>

      {/* 測試結果 */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">測試結果</h2>
        {Object.entries(results).map(([key, value]) => (
          <div key={key} className="border rounded-lg p-4">
            <h3 className="font-medium text-gray-800 mb-2">{key}</h3>
            <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-96">
              {JSON.stringify(value, null, 2)}
            </pre>
          </div>
        ))}
        
        {Object.keys(results).length === 0 && (
          <div className="text-gray-500 text-center py-8">
            點擊上方按鈕開始測試...
          </div>
        )}
      </div>
    </div>
  );
};

export default LegacyTestPage;