// frontend/src/contexts/AuthContext.tsx

import React, { createContext, useState, useContext, ReactNode, useCallback } from 'react';
import type { User } from '../App'; // 我們將從 App.tsx 引入統一的 User 型別
import { buildApiUrl } from '../config/api';

interface AuthContextType {
  token: string | null;
  user: User | null; // <-- 新增 user 狀態
  login: (token: string, user: User) => void; // <-- login 函式現在接收 user 物件
  logout: () => void;
  isAuthenticated: boolean;
  authFetch: (url: string, options?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('authToken'));
  // --- ↓↓↓ 新增 user 狀態，並嘗試從 localStorage 讀取 ↓↓↓ ---
  const [user, setUser] = useState<User | null>(() => {
    const storedUser = localStorage.getItem('user');
    try {
      return storedUser ? JSON.parse(storedUser) : null;
    } catch (e) {
      return null;
    }
  });

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('authToken', newToken);
    localStorage.setItem('user', JSON.stringify(newUser)); // <-- 將 user 物件存入 localStorage
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('authToken');
    localStorage.removeItem('user'); // <-- 登出時一併移除
  };

  const isAuthenticated = !!token;

  const authFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    const newHeaders = new Headers(options.headers);
    newHeaders.set('Authorization', `Bearer ${token}`);

    if (!(options.body instanceof FormData)) {
      newHeaders.set('Content-Type', 'application/json');
    }

    const fullUrl = buildApiUrl(url);
    const response = await fetch(fullUrl, { ...options, headers: newHeaders });

    if (response.status === 401) {
      logout();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    return response;
  }, [token]); // 移除 logout 依賴，避免無限循環

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};