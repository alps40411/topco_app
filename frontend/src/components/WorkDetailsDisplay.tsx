// frontend/src/components/WorkDetailsDisplay.tsx

import React from 'react';
import { Briefcase, Target, Building, Users } from 'lucide-react';

interface WorkDetailsDisplayProps {
  projectName?: string;
  executionWorkName?: string;
  workItemName?: string;
  serviceCompanyName?: string;
  serviceTargetName?: string;
  className?: string;
}

const WorkDetailsDisplay: React.FC<WorkDetailsDisplayProps> = ({
  projectName,
  executionWorkName,
  workItemName,
  serviceCompanyName,
  serviceTargetName,
  className = ""
}) => {
  // 如果沒有任何工作詳情，不顯示組件
  if (!projectName && !executionWorkName && !workItemName && !serviceCompanyName && !serviceTargetName) {
    return null;
  }

  return (
    <div className={`bg-gray-50 rounded-lg p-4 space-y-2 ${className}`}>
      <h4 className="text-sm font-semibold text-gray-600 mb-3">工作詳情</h4>
      
      <div className="space-y-2 text-sm">
        {projectName && (
          <div className="flex items-center space-x-2">
            <Briefcase className="w-4 h-4 text-blue-500" />
            <span className="text-gray-600">工作計畫:</span>
            <span className="font-medium text-gray-800">{projectName}</span>
          </div>
        )}
        
        {executionWorkName && (
          <div className="flex items-center space-x-2">
            <Target className="w-4 h-4 text-green-500" />
            <span className="text-gray-600">執行工作:</span>
            <span className="font-medium text-gray-800">{executionWorkName}</span>
          </div>
        )}
        
        {workItemName && (
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center">
              <div className="w-2 h-2 bg-white rounded-full"></div>
            </div>
            <span className="text-gray-600">工作項目:</span>
            <span className="font-medium text-gray-800">{workItemName}</span>
          </div>
        )}
        
        {serviceCompanyName && (
          <div className="flex items-center space-x-2">
            <Building className="w-4 h-4 text-orange-500" />
            <span className="text-gray-600">服務公司:</span>
            <span className="font-medium text-gray-800">{serviceCompanyName}</span>
          </div>
        )}
        
        {serviceTargetName && (
          <div className="flex items-center space-x-2">
            <Users className="w-4 h-4 text-pink-500" />
            <span className="text-gray-600">服務對象:</span>
            <span className="font-medium text-gray-800">{serviceTargetName}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkDetailsDisplay;