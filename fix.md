# 全端系統效能審計報告

## 1. 問題摘要 (Executive Summary)

本審計發現系統在前後端及資料庫互動中存在幾個關鍵的效能瓶頸。若不加以解決，隨著資料量與使用者數量的增長，系
統的回應速度與穩定性將面臨嚴峻挑戰。目前最主要的效能瓶頸可歸結為以下三點：

1.  後端嚴重的 N+1 查詢問題：在服務層（尤其
    legacy_service_v2.py）中，存在大量在迴圈中單獨查詢資料庫的模式。這是最緊急且影響最大的問題，會導致 API
    回應時間呈線性增長。
1.  解決後端 N+1 查詢 (Severity: Critical)：此問題會讓資料庫負載劇增，是導致 API 變慢的根本原因。修復後，相關
    API 的效能預期會有數量級的提升。

- 檔案路徑：frontend/src/contexts/AuthContext.tsx
  `typescript
  // frontend/src/contexts/AuthContext.tsx (問題程式碼)
  export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  // ... state definitions ...

        return (
          <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
          </AuthContext.Provider>
        );
      };
      `

  改善建議*：使用 useMemo hook 來快取 value 物件。只有當其依賴項（例如 user 或
  loading）真正發生變化時，才會產生新的物件引用，從而避免不必要的子元件渲染。
  建議程式碼*：

`typescript
// frontend/src/contexts/AuthContext.tsx (建議修改)
import React, { useMemo, ... } from 'react';

      export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
        // ... state definitions ...

        const memoizedValue = useMemo(
          () => ({ user, loading, login, logout }),
          [user, loading] // 依賴項應包含所有會變動的值
        );

        return (
          <AuthContext.Provider value={memoizedValue}>
            {children}
          </AuthContext.Provider>
        );
      };
      `

#### 問題點 2：重複的 API 請求與請求瀑布

- 檔案路徑：frontend/src/hooks/useDataSync.ts 及使用此 hook 的多個元件 (如 DataInputTab.tsx)。
  `typescript
        useEffect(() => {
          const fetchInitialData = async () => {
            setLoading(true);
            try {
              const [userData, optionsData] = await Promise.all([
                api.fetch('/api/users/me'),
                api.fetch('/api/work-options')
              ]);
              setUserData(userData);
              setOptionsData(optionsData);
            } catch (error) {
              setError(error);
            } finally {
              setLoading(false);
            }
          };
          fetchInitialData();
        }, []);
        `

#### 問題點 3：複雜元件缺乏輸入防抖 (Debounce)

- 檔案路徑：frontend/src/components/CascadingWorkSelector.tsx
  `typescript
  // 1. 建立一個 useDebounce hook
  function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
  const handler = setTimeout(() => {
  setDebouncedValue(value);
  }, delay);
  return () => {
  clearTimeout(handler);
  };
  }, [value, delay]);
  return debouncedValue;
  }

      // 2. 在 CascadingWorkSelector.tsx 中使用
      const [searchTerm, setSearchTerm] = useState('');
      const debouncedSearchTerm = useDebounce(searchTerm, 300); // 300ms 延遲

      useEffect(() => {
        if (debouncedSearchTerm) {
          // 在這裡發起 API 請求
          api.fetch(/api/work-items?search=${debouncedSearchTerm}).then(...);
        }
      }, [debouncedSearchTerm]); // 只在 debouncedSearchTerm 改變時觸發

      // JSX
      <input onChange={(e) => setSearchTerm(e.target.value)} />
      `

### 後端分析 (Backend Analysis)

#### 問題點 1：嚴重的 N+1 查詢問題

- 檔案路徑：backend/app/services/legacy_service_v2.py (此為最可能的檔案，但模式可能存在於多個服務中)
  `python # backend/app/services/some_review_service.py (問題模式)
  def get_reviews_with_author_names(db: Session):
  reviews = db.query(models.Review).all() # 第一次查詢

        results = []
        for review in reviews:
          # 在迴圈中進行了 N 次額外查詢
          author = db.query(models.User).filter(models.User.id == review.author_id).first()
          results.append({
            "review_content": review.content,
            "author_name": author.full_name
          })
        return results
      `

  改善建議*：使用 SQLAlchemy 的預載入 (Eager Loading) 機制，在第一次查詢時就透過 JOIN
  將關聯資料一併取出。最常用的方法是 joinedload。
  建議程式碼*：

`python # backend/app/services/some_review_service.py (建議修改)
from sqlalchemy.orm import joinedload

      def get_reviews_with_author_names(db: Session):
        # 使用 joinedload，SQLAlchemy 會產生一個 JOIN 查詢
        reviews = db.query(models.Review).options(
          joinedload(models.Review.author) # 假設 Review 模型中有名為 'author' 的 relationship
        ).all()

        # 現在 review.author 已經被填充，無需額外查詢
        results = [{
          "review_content": review.content,
          "author_name": review.author.full_name
        } for review in reviews]
        return results
      `

問題點 2：在記憶體中處理應由資料庫完成的工作

- 檔案路徑：backend/app/api/reports.py
  `python # backend/app/api/reports.py (問題模式)
  @router.get("/pending_reports")
  def get_pending_reports(db: Session):
  all_reports = db.query(models.Report).all() # 獲取所有報告

        # 在 Python 中進行篩選
        pending_reports = [r for r in all_reports if r.status == 'pending']
        return pending_reports
      `

  改善建議*：將篩選、排序和分頁邏輯直接移入 SQLAlchemy 查詢中，讓資料庫完成這些操作。
  建議程式碼*：

`python
      # backend/app/api/reports.py (建議修改)
      @router.get("/pending_reports")
      def get_pending_reports(db: Session, skip: int = 0, limit: int = 100):
        # 直接在資料庫層級進行篩選、排序和分頁
        pending_reports = db.query(models.Report)\
                            .filter(models.Report.status == 'pending')\
                            .order_by(models.Report.created_at.desc())\
                            .offset(skip)\
                            .limit(limit)\
                            .all()
        return pending_reports
      `

### 資料庫與 ORM (Database & ORM)

#### 問題點 1：關鍵查詢欄位缺少索引

- 相關程式碼與查詢模式：
  `python # backend/app/models/some_model.py (建議修改)
  from sqlalchemy import Column, String, Date, ForeignKey, Integer

      class Report(Base):
          __tablename__ = 'reports'
          id = Column(Integer, primary_key=True)
          # 為經常查詢的日期欄位添加索引
          doc_date = Column(Date, index=True)
          # 為經常查詢的狀態欄位添加索引
          status = Column(String, index=True)
          # 外鍵欄位也應有索引
          submitter_id = Column(Integer, ForeignKey('users.id'), index=True)
      `
      如果您使用 Alembic

  進行資料庫遷移，更新模型後，它可以自動生成建立索引的遷移腳本。如果手動管理，則需執行 CREATE INDEX SQL
  命令。

4. 總結與後續步驟 (Conclusion & Next Steps)
   建議的優化排程如下：

1. 短期 (1-2 週)：
1. 中期 (1 個月內)：
   完成以上優化後，系統的整體效能、穩定性和擴展性將得到質的飛躍，為未來的業務發展奠定堅實的基礎。
