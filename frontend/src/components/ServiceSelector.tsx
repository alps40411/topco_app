// frontend/src/components/ServiceSelector.tsx

import React from "react";
import SearchableDropdown from "./SearchableDropdown";
import SimpleDropdown from "./SimpleDropdown";

interface ServiceSelectorProps {
  selectedCompanyId?: string;
  selectedTargetId?: string;
  onCompanyChange: (companyId?: string) => void;
  onTargetChange: (targetId?: string) => void;
  serviceCompanies?: Array<{ id: string; cocode: string; coabbv: string }>;
  serviceTargets?: Array<{
    cocode: string;
    coabbv: string;
    deptno: string;
    deptabbv: string;
    empno: string;
    empnamec: string;
  }>;
  required?: boolean;
  className?: string;
}

const ServiceSelector: React.FC<ServiceSelectorProps> = ({
  selectedCompanyId,
  selectedTargetId,
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

  const targetOptions = serviceTargets.map((target, index) => ({
    id: target.empno || `target-${index}`,
    name: target.empnamec || target.empno,
  }));

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 服務公司選擇 */}
      <SimpleDropdown
        label="服務公司"
        placeholder="請選擇服務公司"
        options={companyOptions}
        selectedValue={selectedCompanyId}
        onSelectionChange={onCompanyChange}
        isLoading={false}
        required={required}
      />

      {/* 服務對象選擇 */}
      <SearchableDropdown
        label="服務對象"
        placeholder="請選擇服務對象"
        options={targetOptions}
        selectedValue={selectedTargetId}
        onSelectionChange={onTargetChange}
        isLoading={false}
        required={required}
      />
    </div>
  );
};

export default ServiceSelector;
