// frontend/src/components/AiEnhanceButton.tsx
// Split Button 設計: 左邊執行潤飾,右邊選擇模型

import React, { useState, useRef, useEffect } from "react";
import { Wand2, ChevronDown, Check } from "lucide-react";
import { AiService } from "./AiServiceSelector";

interface AiEnhanceButtonProps {
  selectedService: AiService;
  onServiceChange: (service: AiService) => void;
  onEnhance: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  className?: string;
  children?: React.ReactNode;
}

interface ServiceConfig {
  value: AiService;
  label: string;
  logo: string;
  badge?: string;
}

const AiEnhanceButton: React.FC<AiEnhanceButtonProps> = ({
  selectedService,
  onServiceChange,
  onEnhance,
  disabled = false,
  isLoading = false,
  className = "",
  children,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const services: ServiceConfig[] = [
    {
      value: "claude",
      label: "Claude",
      logo: "/MyReportAI_Weekly/claude.svg",
      badge: "推薦",
    },
    {
      value: "phison",
      label: "Phison LLM",
      logo: "/MyReportAI_Weekly/phison.png",
    },
  ];

  const selectedConfig =
    services.find((s) => s.value === selectedService) ?? services[0];

  // 點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleSelect = (service: AiService) => {
    onServiceChange(service);
    setIsOpen(false);
  };

  return (
    <div className={`relative inline-flex ${className}`} ref={dropdownRef}>
      {/* Split Button 容器 */}
      <div className="inline-flex rounded-lg overflow-hidden border border-purple-200">
        {/* 左側: 執行潤飾按鈕 */}
        <button
          type="button"
          onClick={onEnhance}
          disabled={disabled || isLoading}
          className="
            inline-flex items-center justify-center gap-2
            px-3 sm:px-4 h-10
            text-xs sm:text-sm font-medium
            bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700
            hover:from-purple-200 hover:to-blue-200
            transition-all duration-200
            disabled:from-gray-100 disabled:to-gray-100
            disabled:text-gray-400 disabled:cursor-not-allowed
          "
        >
          {/* AI Logo */}
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-transparent border-t-purple-500 rounded-full animate-spin"></div>
          ) : (
            <img
              src={selectedConfig.logo}
              alt={selectedConfig.label}
              className="w-4 h-4 object-contain"
            />
          )}

          {/* 文字 */}
          {children || (
            <>
              <span className="hidden sm:inline whitespace-nowrap">
                潤飾全部
              </span>
              <span className="sm:hidden whitespace-nowrap">潤飾</span>
            </>
          )}
        </button>

        {/* 右側: 模型選擇按鈕 */}
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled || isLoading}
          className="
            inline-flex items-center justify-center
            px-2 border-l border-purple-300
            bg-gradient-to-r from-purple-100 to-blue-100 text-purple-700
            hover:from-purple-200 hover:to-blue-200
            transition-all duration-200
            disabled:from-gray-100 disabled:to-gray-100
            disabled:text-gray-400 disabled:cursor-not-allowed
          "
        >
          <ChevronDown
            className={`w-4 h-4 transition-transform duration-200 ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </button>
      </div>

      {/* 下拉選單 */}
      {isOpen && (
        <div
          className="
            absolute z-50 mt-2
            bg-white border border-gray-200 rounded-lg shadow-lg
            py-1
            animate-fade-in-scale
          "
          style={{ top: "100%", right: 0 }}
        >
          {services.map((service) => (
            <button
              key={service.value}
              type="button"
              onClick={() => handleSelect(service.value)}
              className={`
                w-full flex items-center gap-3 px-3 py-2
                text-sm text-left whitespace-nowrap
                hover:bg-gray-50
                transition-colors duration-150
                ${service.value === selectedService ? "bg-purple-50" : ""}
              `}
            >
              {/* 選中勾勾 (固定寬度) */}
              <div className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                {service.value === selectedService && (
                  <Check className="w-4 h-4 text-purple-600" />
                )}
              </div>

              {/* AI Logo (固定寬度) */}
              <img
                src={service.logo}
                alt={service.label}
                className="w-4 h-4 flex-shrink-0 object-contain"
              />

              {/* Label */}
              <span
                className={`${
                  service.value === selectedService
                    ? "font-medium text-gray-900"
                    : "text-gray-700"
                }`}
              >
                {service.label}
              </span>

              {/* Badge */}
              {service.badge && (
                <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded">
                  {service.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* 動畫樣式 */}
      <style>{`
        @keyframes fade-in-scale {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(-4px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        .animate-fade-in-scale {
          animation: fade-in-scale 0.15s ease-out forwards;
        }
      `}</style>
    </div>
  );
};

export default AiEnhanceButton;
