# backend/app/services/phison_ai_service.py

import aiohttp
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.config import settings
from app.services import ai_prompts

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
        # 跳過 SSL 證書驗證（因為內網 IP 使用自簽名證書）
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
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

    except aiohttp.ClientConnectorError as e:
        logger.warning(f"⚠️ Phison 服務器連接失敗 ({settings.PHISON_API_URL}): 服務器可能離線或網絡不可達")
        logger.debug(f"連接錯誤詳情: {str(e)}")
        return None
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
        raise ConnectionError(f"無法連接到 Phison AI 服務 ({settings.PHISON_API_URL})，請檢查服務狀態或切換到 Claude 服務")

    # Phison API 只有單一 content 欄位，將共用的 system prompt 與 user prompt 合併送出
    user_prompt = (
        f"{ai_prompts.DAILY_ENHANCE_SYSTEM}\n\n"
        + ai_prompts.build_daily_enhance_user_prompt(project_name, original_content, reference_texts)
    )

    # 呼叫 Phison Chat API
    chat_url = f"{settings.PHISON_API_URL}/api/Chat"
    payload = {
        "content": user_prompt,
        "maxTokens": 1500,
        "temperature": 1
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"調用 Phison Chat API: {chat_url}")
        # 跳過 SSL 證書驗證
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
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

async def get_phison_weekly_report(
    original_content: str,
    job_item: str,
    subject: str,
    reference_texts: List[str] = []
) -> str:
    """
    使用 Phison LLM API 將週報內容潤飾成專業格式（週報專用）

    Args:
        original_content: 原始週報內容（純文字）
        job_item: 工作項目名稱
        subject: 週報主題
        reference_texts: 參考資料文字列表

    Returns:
        潤飾後的週報內容
    """
    logger.info(f"開始使用 Phison AI 生成週報內容，工作項目: {job_item}")

    # 取得 token
    token = await _get_phison_token()
    if not token:
        raise ConnectionError(f"無法連接到 Phison AI 服務 ({settings.PHISON_API_URL})，請檢查服務狀態或切換到 Claude 服務")

    # 週報專用 prompt（簡化版，避免過長）
    system_instruction = ai_prompts.WEEKLY_ENHANCE_SYSTEM_COMPACT

    # 組合參考資料
    reference_section = ""
    if reference_texts:
        combined_references = "\n\n".join(reference_texts[:3])  # 最多3個參考
        if len(combined_references) > 1000:
            combined_references = combined_references[:1000]
        reference_section = f"\n\n參考資料：{combined_references}"

    user_prompt = (
        f"{system_instruction}\n\n"
        f"工作項目：{job_item}\n"
        f"主題：{subject}\n\n"
        f"請潤飾以下內容：\n{original_content}"
        f"{reference_section}"
    )

    # 呼叫 Phison Chat API
    chat_url = f"{settings.PHISON_API_URL}/api/Chat"
    payload = {
        "content": user_prompt,
        "maxTokens": 1500,
        "temperature": 0.2
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"調用 Phison Chat API (週報): {chat_url}")
        logger.info(f"Prompt 長度: {len(user_prompt)} 字符")
        
        # 跳過 SSL 證書驗證
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                chat_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Phison Chat API 失敗: {response.status}")
                    logger.error(f"錯誤內容: {error_text[:500]}")
                    raise Exception(f"Phison AI 服務回應錯誤 (HTTP {response.status})")

                # 解析 Phison API 回應格式
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
