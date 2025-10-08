// frontend/src/components/ServiceSelector.tsx

import React from "react";
import SearchableDropdown from "./SearchableDropdown";
import SimpleDropdown from "./SimpleDropdown";

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

  const handleCompanyChange = (companyId?: string | number) => {
    const id = companyId?.toString();
    const company = serviceCompanies.find(c => c.cocode === id || c.id === id);
    onCompanyChange(id, company);
  };

  const handleTargetChange = (targetId?: string | number) => {
    const id = targetId?.toString();
    const target = serviceTargets.find(t => t.empno === id);
    onTargetChange(id, target);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 服務公司選擇 */}
      <SimpleDropdown
        label="服務公司"
        placeholder="請選擇服務公司"
        options={companyOptions}
        selectedValue={selectedCompanyId}
        onSelectionChange={handleCompanyChange}
        isLoading={false}
        required={required}
      />

      {/* 服務對象選擇 */}
      <SearchableDropdown
        label="服務對象"
        placeholder="請選擇服務對象"
        options={targetOptions}
        selectedValue={selectedTargetId}
        onSelectionChange={handleTargetChange}
        isLoading={false}
        required={required}
      />
    </div>
  );
};

export default ServiceSelector;
