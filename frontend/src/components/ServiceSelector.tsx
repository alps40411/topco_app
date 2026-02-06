// frontend/src/components/ServiceSelector.tsx

import React from "react";
import SearchableDropdown from "./SearchableDropdown";

export interface ServiceCompany {
  id?: string;
  cocode: string;
  coabbv: string;
}

export interface ServiceTarget {
  cocode: string;
  coabbv: string;
  deptno: string;
  deptabbv: string;
  empno: string;
  empnamec: string;
}

interface ServiceSelectorProps {
  selectedCompanyId?: string;
  selectedTargetId?: string;
  selectedTargetCocode?: string; // 服務對象所屬公司代碼
  onCompanyChange: (companyId?: string, company?: ServiceCompany) => void;
  onTargetChange: (targetId?: string, target?: ServiceTarget) => void;
  serviceCompanies?: ServiceCompany[];
  serviceTargets?: ServiceTarget[];
  required?: boolean;
  className?: string;
}

const ServiceSelector: React.FC<ServiceSelectorProps> = ({
  selectedCompanyId,
  selectedTargetId,
  selectedTargetCocode,
  onCompanyChange,
  onTargetChange,
  serviceCompanies = [],
  serviceTargets = [],
  required = false,
  className = "",
}) => {
  const companyOptions = serviceCompanies.map((company, index) => ({
    id: company.cocode || company.id || `company-${index}`,
    name: company.coabbv || company.cocode,
  }));

  // 將完整資料傳遞給 SearchableDropdown，支援多欄位搜尋和顯示
  const targetOptions = serviceTargets.map((target, index) => ({
    id:
      target.cocode && target.empno
        ? `${target.cocode}_${target.empno}` // 使用組合鍵避免 ID 重複
        : `target-${index}`,
    name: target.empnamec || target.empno,
    // 新增額外資料以支援多欄位搜尋和顯示
    empno: target.empno,
    empnamec: target.empnamec,
    coabbv: target.coabbv,
    deptabbv: target.deptabbv,
    cocode: target.cocode,
    deptno: target.deptno,
  }));

  const handleCompanyChange = (companyId?: string | number) => {
    const id = companyId?.toString();
    const company = serviceCompanies.find(
      (c) => c.cocode === id || c.id === id
    );
    onCompanyChange(id, company);
  };

  const handleTargetChange = (targetId?: string | number) => {
    const id = targetId?.toString();

    if (!id) {
      onTargetChange(undefined, undefined);
      return;
    }

    // 解析組合鍵 "cocode_empno"
    const [cocode, empno] = id.split("_");
    const target = serviceTargets.find(
      (t) => t.cocode === cocode && t.empno === empno
    );

    onTargetChange(target?.empno, target);
  };

  // 將 selectedTargetId（empno）轉換為組合鍵格式
  const computedSelectedTargetId = React.useMemo(() => {
    if (!selectedTargetId) return undefined;

    // 優先使用 selectedTargetCocode（服務對象所屬公司）來構建組合鍵
    if (selectedTargetCocode) {
      const exists = serviceTargets.some(
        (t) => t.cocode === selectedTargetCocode && t.empno === selectedTargetId
      );
      if (exists) {
        return `${selectedTargetCocode}_${selectedTargetId}`;
      }
    }

    // Fallback：找到第一個匹配的員工
    const target = serviceTargets.find((t) => t.empno === selectedTargetId);
    if (target?.cocode) {
      return `${target.cocode}_${selectedTargetId}`;
    }

    return selectedTargetId;
  }, [selectedTargetId, selectedTargetCocode, serviceTargets]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 服務公司選擇 - 可搜尋，顯示 12 筆 */}
      <SearchableDropdown
        label="服務公司"
        placeholder="請選擇服務公司"
        options={companyOptions}
        selectedValue={selectedCompanyId}
        onSelectionChange={handleCompanyChange}
        isLoading={false}
        required={required}
        enableMultiFieldSearch={false}
        searchFields={["name"]}
        searchPlaceholder="輸入公司名稱搜尋..."
        displayTemplate="default"
        maxVisibleItems={12}
      />

      {/* 服務對象選擇 - 啟用多欄位搜尋和顯示，顯示 8 筆 */}
      <SearchableDropdown
        label="服務對象"
        placeholder="請選擇服務對象"
        options={targetOptions}
        selectedValue={computedSelectedTargetId}
        onSelectionChange={handleTargetChange}
        isLoading={false}
        required={required}
        enableMultiFieldSearch={true}
        searchFields={["empno", "empnamec", "coabbv", "deptabbv"]}
        displayTemplate="table"
        maxVisibleItems={8}
      />
    </div>
  );
};

export default ServiceSelector;
