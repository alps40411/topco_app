// frontend/src/components/ServiceSelector.tsx

import React, { useState, useEffect } from 'react';
import SearchableDropdown from './SearchableDropdown';
import type { ServiceCompany, ServiceTarget } from '../App';

interface ServiceSelectorProps {
  selectedCompanyId?: number;
  selectedTargetId?: number;
  onCompanyChange: (companyId?: number) => void;
  onTargetChange: (targetId?: number) => void;
  required?: boolean;
  className?: string;
}

const ServiceSelector: React.FC<ServiceSelectorProps> = ({
  selectedCompanyId,
  selectedTargetId,
  onCompanyChange,
  onTargetChange,
  required = false,
  className = ""
}) => {
  const [companies, setCompanies] = useState<ServiceCompany[]>([]);
  const [targets, setTargets] = useState<ServiceTarget[]>([]);
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(false);
  const [isLoadingTargets, setIsLoadingTargets] = useState(false);

  // 載入服務公司列表 - 直接使用假資料
  const fetchServiceCompanies = async () => {
    setIsLoadingCompanies(true);
    // 模擬API請求延遲
    setTimeout(() => {
      setCompanies([
        { id: 1, name: '台灣積體電路製造股份有限公司', is_active: true },
        { id: 2, name: '宏達國際電子股份有限公司', is_active: true },
        { id: 3, name: '廣達電腦股份有限公司', is_active: true },
        { id: 4, name: '仁寶電腦工業股份有限公司', is_active: true },
        { id: 5, name: '和碩聯合科技股份有限公司', is_active: true },
        { id: 6, name: '緯創資通股份有限公司', is_active: true },
        { id: 7, name: '英業達股份有限公司', is_active: true },
        { id: 8, name: '華碩電腦股份有限公司', is_active: true },
        { id: 9, name: '微星科技股份有限公司', is_active: true },
        { id: 10, name: '技嘉科技股份有限公司', is_active: true },
      ]);
      setIsLoadingCompanies(false);
    }, 300);
  };

  // 載入服務對象列表 - 直接使用假資料
  const fetchServiceTargets = async () => {
    setIsLoadingTargets(true);
    // 模擬API請求延遲
    setTimeout(() => {
      const allTargets = [
        // 台積電相關
        { id: 1, name: '台積電 - 總公司', company_id: 1, is_active: true },
        { id: 2, name: '台積電 - 竹科廠', company_id: 1, is_active: true },
        { id: 3, name: '台積電 - 中科廠', company_id: 1, is_active: true },
        { id: 4, name: '台積電 - 南科廠', company_id: 1, is_active: true },
        // HTC相關
        { id: 5, name: 'HTC - 總公司', company_id: 2, is_active: true },
        { id: 6, name: 'HTC - 研發部門', company_id: 2, is_active: true },
        // 廣達相關
        { id: 7, name: '廣達 - 總公司', company_id: 3, is_active: true },
        { id: 8, name: '廣達 - 桃園廠', company_id: 3, is_active: true },
        // 仁寶相關
        { id: 15, name: '仁寶 - 總公司', company_id: 4, is_active: true },
        { id: 16, name: '仁寶 - 生產廠', company_id: 4, is_active: true },
        // 和碩相關
        { id: 17, name: '和碩 - 總公司', company_id: 5, is_active: true },
        { id: 18, name: '和碩 - 研發中心', company_id: 5, is_active: true },
        // 通用選項
        { id: 9, name: '全集團通用', company_id: null, is_active: true },
        { id: 10, name: '外部客戶', company_id: null, is_active: true },
        { id: 11, name: '政府機關', company_id: null, is_active: true },
        { id: 12, name: '學術機構', company_id: null, is_active: true },
        { id: 13, name: '合作夥伴', company_id: null, is_active: true },
        { id: 14, name: '供應商', company_id: null, is_active: true },
      ];

      // 根據選擇的公司過濾
      if (selectedCompanyId) {
        setTargets(allTargets.filter(target => 
          target.company_id === selectedCompanyId || target.company_id === null
        ));
      } else {
        setTargets(allTargets);
      }
      setIsLoadingTargets(false);
    }, 200);
  };

  useEffect(() => {
    fetchServiceCompanies();
    fetchServiceTargets();
  }, []);

  useEffect(() => {
    fetchServiceTargets();
    // 如果選擇的服務對象不屬於當前選擇的公司，清除它
    if (selectedTargetId) {
      const currentTarget = targets.find(t => t.id === selectedTargetId);
      if (currentTarget && currentTarget.company_id !== null && currentTarget.company_id !== selectedCompanyId) {
        onTargetChange(undefined);
      }
    }
  }, [selectedCompanyId]);

  const handleCompanyChange = (companyId?: number) => {
    onCompanyChange(companyId);
    // 不自動清除服務對象選擇，讓用戶自己決定
  };

  const companyOptions = companies.map(company => ({
    id: company.id,
    name: company.name
  }));

  const targetOptions = targets.map(target => ({
    id: target.id,
    name: target.name
  }));

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 服務公司選擇 */}
      <SearchableDropdown
        label="服務公司"
        placeholder="請選擇服務公司"
        options={companyOptions}
        selectedValue={selectedCompanyId}
        onSelectionChange={handleCompanyChange}
        isLoading={isLoadingCompanies}
        required={required}
      />

      {/* 服務對象選擇 */}
      <SearchableDropdown
        label="服務對象"
        placeholder="請選擇服務對象"
        options={targetOptions}
        selectedValue={selectedTargetId}
        onSelectionChange={onTargetChange}
        isLoading={isLoadingTargets}
        required={required}
      />
    </div>
  );
};

export default ServiceSelector;