// frontend/src/components/AiServiceSelector.tsx

import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

export type AiService = "aoai" | "phison";

interface AiServiceSelectorProps {
  selectedService: AiService;
  onServiceChange: (service: AiService) => void;
  disabled?: boolean;
  className?: string;
  buttonClassName?: string;
  showLabel?: boolean;
}

interface ServiceConfig {
  value: AiService;
  label: string;
  logo: string;
  badge?: string;
}

const AiServiceSelector: React.FC<AiServiceSelectorProps> = ({
  selectedService,
  onServiceChange,
  disabled = false,
  className = "",
  buttonClassName = "",
  showLabel = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const services: ServiceConfig[] = [
    {
      value: "aoai",
      label: "Azure OpenAI",
      logo: "/MyReportAI/Microsoft_Azure.png",
      badge: "推薦",
    },
    {
      value: "phison",
      label: "Phison LLM",
      logo: "/MyReportAI/phison.png",
    },
  ];

  const selectedConfig = services.find((s) => s.value === selectedService)!;

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
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* 觸發按鈕 */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          inline-flex items-center gap-2 px-3 py-2
          text-sm font-medium
          bg-white border border-gray-300 rounded-lg
          hover:bg-gray-50 hover:border-gray-400
          focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-all duration-200
          ${buttonClassName}
        `}
      >
        {/* AI Logo */}
        <img
          src={selectedConfig.logo}
          alt={selectedConfig.label}
          className="w-4 h-4 object-contain"
        />

        {/* Label (可選) */}
        {showLabel && (
          <span className="text-gray-700">{selectedConfig.label}</span>
        )}

        {/* 下拉箭頭 */}
        <ChevronDown
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* 下拉選單 */}
      {isOpen && (
        <div
          className="
            absolute z-50 mt-2
            bg-white border border-gray-200 rounded-lg shadow-lg
            py-1
            animate-fade-in-scale
          "
          style={{ top: "100%" }}
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
                ${
                  service.value === selectedService
                    ? "bg-purple-50"
                    : ""
                }
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

export default AiServiceSelector;
