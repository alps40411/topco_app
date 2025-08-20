// frontend/src/hooks/useHasSubordinates.ts

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";

export const useHasSubordinates = () => {
  const { authFetch } = useAuth();
  const [hasSubordinates, setHasSubordinates] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkSubordinates = async () => {
      try {
        setLoading(true);
        const response = await authFetch("/api/supervisor/has-subordinates");

        if (response.ok) {
          const data = await response.json();
          setHasSubordinates(data.has_subordinates);
          setError(null);
        } else {
          setHasSubordinates(false);
          setError("檢查下屬關係失敗");
        }
      } catch (err) {
        setHasSubordinates(false);
        setError("網路錯誤");
        console.error("Error checking subordinates:", err);
        // 額外日誌幫助調試
        if (err instanceof Error) {
          console.error("Error details:", err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    checkSubordinates();
  }, [authFetch]);

  return { hasSubordinates, loading, error };
};
