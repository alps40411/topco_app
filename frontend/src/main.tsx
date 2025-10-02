import React from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useSearchParams,
} from "react-router-dom";
import App from "./App.tsx";
import LoginPage from "./components/LoginPage.tsx";
import RedirectHandler from "./components/RedirectHandler.tsx";
import { AuthProvider, useAuth } from "./contexts/AuthContext.tsx";
import "./index.css";

// This component checks for 'daily_no' and decides whether to redirect or render the app.
const RootHandler = () => {
  const [searchParams] = useSearchParams();
  // If daily_no exists in the URL, it's a link from an email that needs redirection.
  if (searchParams.has("daily_no")) {
    return <RedirectHandler />;
  }
  // Otherwise, render the main application.
  return <App />;
};

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated, token, user } = useAuth();

  console.log("🛡️ ProtectedRoute - 認證檢查:", {
    isAuthenticated,
    hasToken: !!token,
    hasUser: !!user,
    tokenLength: token?.length || 0,
  });

  // 如果有 token 但 isAuthenticated 為 false，可能是初始化問題
  // 在這種情況下，我們應該等待初始化完成
  if (token && !isAuthenticated) {
    console.log("⏳ ProtectedRoute - 等待認證初始化...");
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">驗證中...</p>
        </div>
      </div>
    );
  }

  // 檢查是否真的需要跳轉到登入頁面
  if (!isAuthenticated) {
    console.log("❌ ProtectedRoute - 未認證，準備跳轉到登入頁面");
    // 確保清理本地存儲
    if (!token) {
      localStorage.removeItem("authToken");
      localStorage.removeItem("user");
    }
  }

  console.log(
    "🔒 ProtectedRoute - 認證結果:",
    isAuthenticated ? "已認證" : "未認證"
  );
  return isAuthenticated ? children : <Navigate to="login" replace />;
};

const AppWithAuth = () => {
  return (
    <AuthProvider>
      <Router basename="/MyReportAI/">
        <Routes>
          <Route path="login" element={<LoginPage />} />

          {/* Main application route now uses RootHandler */}
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <RootHandler />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

ReactDOM.createRoot(document.getElementById("root")!).render(<AppWithAuth />);
