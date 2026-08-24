# backend/scripts/verify_claude.py
# Claude AI 服務部署驗證腳本。
# 在後端伺服器上執行：python scripts/verify_claude.py
# 依序驗證：套件版本 → 金鑰設定 → api.anthropic.com 連線 → 潤飾呼叫 → 結構化輸出。

import asyncio
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def step(name: str, ok: bool, detail: str = ""):
    mark = "✅" if ok else "❌"
    print(f"{mark} {name}" + (f"：{detail}" if detail else ""))
    if not ok:
        sys.exit(1)


def main():
    # 1. 套件版本
    try:
        import anthropic
    except ImportError:
        step("anthropic 套件", False, "未安裝，請執行 pip install -r requirements.txt")
    major = int(anthropic.__version__.split(".")[0])
    step("anthropic 套件", major >= 1, f"版本 {anthropic.__version__}" + ("" if major >= 1 else "（需要 >= 1.0.0，請重新安裝依賴）"))

    # 2. 金鑰設定（Claude Platform on AWS 或第一方 API 二擇一）
    from app.core.config import settings
    if settings.ANTHROPIC_AWS_WORKSPACE_ID:
        step(
            "Claude Platform on AWS 設定",
            bool(settings.AWS_REGION) and bool(settings.ANTHROPIC_AWS_API_KEY),
            f"workspace={settings.ANTHROPIC_AWS_WORKSPACE_ID}, region={settings.AWS_REGION or '未設定'}, "
            f"api_key={'已設定' if settings.ANTHROPIC_AWS_API_KEY else '未設定（將改用 AWS IAM 憑證鏈）'}",
        )
        api_host = f"aws-external-anthropic.{settings.AWS_REGION}.api.aws"
    else:
        step("ANTHROPIC_API_KEY", bool(settings.ANTHROPIC_API_KEY), "已設定" if settings.ANTHROPIC_API_KEY else "未設定，請在 backend/.env 加入")
        api_host = "api.anthropic.com"
    print(f"   模型：{settings.CLAUDE_MODEL}")

    # 3. 網路連線（正式機防火牆驗證的第一關）
    try:
        with socket.create_connection((api_host, 443), timeout=10):
            step(f"{api_host}:443 連線", True)
    except OSError as e:
        step(f"{api_host}:443 連線", False, f"{e}（請確認防火牆是否放行對外 HTTPS）")

    # 4. 實際潤飾呼叫（驗證金鑰、模型 ID、fallback 參數）
    from app.services import claude_ai_service

    async def run_checks():
        result = await claude_ai_service.get_ai_enhanced_report(
            original_content="完成後端 API 開發，修正登入問題",
            project_name="部署驗證測試",
        )
        step("日報潤飾呼叫", bool(result), f"回應 {len(result)} 字")
        print("   --- 回應預覽 ---")
        print("   " + result[:200].replace("\n", "\n   "))

        suggestions = await claude_ai_service.generate_reply_suggestions(
            system_prompt="你是部門主管，請生成回覆建議。",
            user_prompt="請為員工「測試員」的日報「完成系統部署驗證」生成3個回覆建議。",
        )
        step("主管建議結構化輸出", len(suggestions) > 0, f"取得 {len(suggestions)} 筆建議")

    asyncio.run(run_checks())
    print("\n🎉 全部驗證通過，Claude AI 服務可正常使用。")


if __name__ == "__main__":
    main()
