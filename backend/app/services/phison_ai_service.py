# backend/app/services/phison_ai_service.py

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

# Token 快取 (24小時有效)
_token_cache = {
    "token": None,
    "expires_at": None
}

async def _get_phison_token() -> Optional[str]:
    """
    取得 Phison API Token (支援 24 小時快取)
    """
    # 檢查快取是否有效
    if _token_cache["token"] and _token_cache["expires_at"]:
        if datetime.now() < _token_cache["expires_at"]:
            logger.info("使用快取的 Phison token")
            return _token_cache["token"]

    # Token 過期或不存在，重新登入
    logger.info("Phison token 已過期或不存在，重新登入...")

    if not settings.PHISON_API_URL or not settings.PHISON_USERNAME or not settings.PHISON_PASSWORD:
        logger.error("Phison API 配置不完整")
        return None

    login_url = f"{settings.PHISON_API_URL}/api/Auth/login"
    login_payload = {
        "username": settings.PHISON_USERNAME,
        "password": settings.PHISON_PASSWORD
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                login_url,
                json=login_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Phison 登入失敗: {response.status} - {error_text}")
                    return None

                result = await response.json()
                token = result.get("token")

                if not token:
                    logger.error("Phison API 回應中沒有 token")
                    return None

                # 快取 token (24小時 - 保守設定為 23 小時)
                _token_cache["token"] = token
                _token_cache["expires_at"] = datetime.now() + timedelta(hours=23)

                logger.info("成功取得 Phison token，快取 23 小時")
                return token

    except aiohttp.ClientError as e:
        logger.error(f"Phison 登入請求失敗: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Phison 登入發生未預期錯誤: {str(e)}")
        return None


async def get_phison_enhanced_report(
    original_content: str,
    project_name: str,
    reference_texts: List[str] = []
) -> str:
    """
    使用 Phison LLM API 將報告內容潤飾成專業格式

    Args:
        original_content: 原始工作內容
        project_name: 專案名稱
        reference_texts: 參考資料文字列表 (從 Document Intelligence 提取)

    Returns:
        潤飾後的報告內容
    """
    logger.info(f"開始使用 Phison AI 生成增強內容，專案: {project_name}")

    # 取得 token
    token = await _get_phison_token()
    if not token:
        raise Exception("無法取得 Phison API Token")

    # 構建 prompt (與 Azure OpenAI 使用相同的格式)
    system_instruction = (
        "你是一位專業、精確且一絲不苟的商業報告助理。\n"
        "你的任務是將使用者在 `<NOTES>` 標籤中提供的零散筆記，轉換為一份採用「進度、計畫、問題」(Progress, Plans, Problems) 框架的每日工作報告。\n\n"
        "請給予我純文字。"
        "你必須嚴格遵守以下三大原則：\n\n"
        "1. **絕對接地原則 (Absolute Grounding Principle)**:\n"
        "   - 報告中的「一、今日進度」部分，必須嚴格且僅僅基於 `<NOTES>` 的文字進行潤飾。\n"
        "   - **絕對禁止**在任何部分添加筆記中未明確提及的**具體細節**（例如：函式庫名稱、錯誤代碼、特定人名、具體數字等）。這是最高指令。\n\n"
        "2. **有限推斷原則 (Limited Inference Principle)**:\n"
        "   - 報告中的「二、明日計畫」部分，允許基於筆記內容進行合理的、高層次的後續步驟建議。\n"
        "   - 如果筆記內容無法推斷出明確的下一步，你必須在該部分誠實地註明「**待下一步規劃。**」。\n\n"
        "3. **問題識別原則 (Problem Identification Principle)**:\n"
        "   - 只有當筆記中**明確提及**了困難、障礙、等待、或不確定的情況時，才能在「三、潛在問題與阻礙」部分中列出。\n"
        "   - 如果筆記中未提及任何問題，你必須在該部分註明「**目前無明顯阻礙。**」，絕不允許臆測或編造問題。"
    )

    # 組合參考資料
    reference_section = ""
    if reference_texts:
        combined_references = "\n\n".join(reference_texts)
        reference_section = f"\n\n<REFERENCES>\n{combined_references}\n</REFERENCES>"

    user_prompt = (
        f"{system_instruction}\n\n"
        f"請為「{project_name}」這個專案，潤飾以下工作內容，並參考附加的資料，生成一份每日工作報告。\n\n"
        f"<NOTES>\n{original_content}\n</NOTES>"
        f"{reference_section}"
    )

    # 呼叫 Phison Chat API
    chat_url = f"{settings.PHISON_API_URL}/api/Chat"
    payload = {
        "content": user_prompt,
        "maxTokens": 1500,
        "temperature": 0.2  # 與 Azure OpenAI 保持一致
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"調用 Phison Chat API: {chat_url}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                chat_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Phison Chat API 失敗: {response.status} - {error_text}")
                    raise Exception(f"Phison AI 服務回應錯誤 (HTTP {response.status})")

                # 解析 Phison API 回應格式
                # 格式: {"choices": [{"message": {"content": "潤飾後內容"}}]}
                result = await response.json()

                if isinstance(result, dict):
                    # 嘗試從 choices[0].message.content 提取
                    if "choices" in result and len(result["choices"]) > 0:
                        message = result["choices"][0].get("message", {})
                        ai_content = message.get("content", "")
                    # 備用: 直接從 content 或 result 提取
                    elif "content" in result:
                        ai_content = result["content"]
                    elif "result" in result:
                        ai_content = result["result"]
                    else:
                        ai_content = str(result)
                else:
                    ai_content = str(result)

                logger.info(f"Phison AI 潤飾成功，回應長度: {len(ai_content)}")
                return ai_content

    except aiohttp.ClientError as e:
        logger.error(f"Phison Chat API 請求失敗: {str(e)}")
        raise Exception(f"無法連接到 Phison AI 服務: {str(e)}")
    except Exception as e:
        logger.error(f"Phison AI 處理失敗: {str(e)}")
        raise


def clear_token_cache():
    """
    清除 token 快取 (用於測試或強制重新登入)
    """
    global _token_cache
    _token_cache = {
        "token": None,
        "expires_at": None
    }
    logger.info("Phison token 快取已清除")
