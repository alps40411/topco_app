# backend/app/services/claude_ai_service.py
# Claude (Anthropic Messages API) 供應商實作。
# 所有呼叫失敗時一律拋出例外，由 API 層轉成 HTTP 錯誤——絕不回傳錯誤字串當內容。

import base64
import json
import logging
from typing import Any, Dict, List, Optional

import anthropic

from app.core.config import settings
from app.services import ai_prompts

logger = logging.getLogger(__name__)

_client = None


class ClaudeServiceError(Exception):
    """Claude AI 服務呼叫失敗（未設定、被拒絕或 API 錯誤）"""


def _get_client():
    global _client
    if _client is not None:
        return _client

    if settings.ANTHROPIC_AWS_WORKSPACE_ID:
        # Claude Platform on AWS：api_key 未設定時 SDK 會改用 AWS IAM 憑證鏈（SigV4）
        if not settings.AWS_REGION:
            raise ClaudeServiceError("Claude Platform on AWS 設定不完整（缺少 AWS_REGION）")
        _client = anthropic.AsyncAnthropicAWS(
            api_key=settings.ANTHROPIC_AWS_API_KEY or None,
            aws_region=settings.AWS_REGION,
            workspace_id=settings.ANTHROPIC_AWS_WORKSPACE_ID,
            timeout=60.0,
            max_retries=2,
        )
    elif settings.ANTHROPIC_API_KEY:
        _client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=60.0,
            max_retries=2,
        )
    else:
        raise ClaudeServiceError(
            "Claude AI 服務未設定（請在 .env 設定 ANTHROPIC_AWS_* 或 ANTHROPIC_API_KEY）"
        )
    return _client


async def _create_message(
    *,
    messages: List[Dict[str, Any]],
    system: Optional[str] = None,
    max_tokens: int = 8192,
    effort: Optional[str] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
):
    """
    統一的 Messages API 呼叫入口。

    - 第一方 API 啟用 server-side refusal fallback（安全分類器拒絕時自動改由備援模型完成）；
      Claude Platform on AWS 不支援此參數，refusal 直接拋出例外
    - stop_reason 為 refusal 時拋出例外
    """
    client = _get_client()
    if timeout:
        client = client.with_options(timeout=timeout)

    output_config: Dict[str, Any] = {}
    if effort:
        output_config["effort"] = effort
    if output_schema:
        output_config["format"] = {"type": "json_schema", "schema": output_schema}

    kwargs: Dict[str, Any] = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if output_config:
        kwargs["output_config"] = output_config

    try:
        if isinstance(client, anthropic.AsyncAnthropicAWS):
            response = await client.messages.create(**kwargs)
        else:
            response = await client.beta.messages.create(
                **kwargs,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
    except anthropic.APIStatusError as e:
        logger.error(f"Claude API 呼叫失敗 (HTTP {e.status_code}): {e.message}")
        raise ClaudeServiceError(f"Claude AI 服務回應錯誤 (HTTP {e.status_code})") from e
    except anthropic.APIConnectionError as e:
        logger.error(f"Claude API 連線失敗: {e}")
        raise ClaudeServiceError("無法連接到 Claude AI 服務，請檢查網路或切換到 Phison 服務") from e

    if response.stop_reason == "refusal":
        stop_details = getattr(response, "stop_details", None)
        explanation = getattr(stop_details, "explanation", None) if stop_details else None
        logger.warning(f"Claude 拒絕處理請求: {explanation}")
        raise ClaudeServiceError(f"AI 因安全政策拒絕處理此內容{f'：{explanation}' if explanation else ''}")

    if response.stop_reason == "max_tokens":
        logger.warning(f"Claude 回應達到 max_tokens 上限 ({max_tokens})，內容可能被截斷")

    return response


def _extract_text(response) -> str:
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise ClaudeServiceError("Claude 回應中沒有文字內容")
    return text


async def get_ai_enhanced_report(
    original_content: str,
    project_name: str,
    reference_texts: List[str] = [],
) -> str:
    """使用 Claude 將日報筆記潤飾為「進度、計畫、問題」格式的每日工作報告。"""
    logger.info(f"調用 Claude 潤飾日報，專案: {project_name}, 模型: {settings.CLAUDE_MODEL}")

    user_prompt = ai_prompts.build_daily_enhance_user_prompt(
        project_name, original_content, reference_texts
    )
    response = await _create_message(
        system=ai_prompts.DAILY_ENHANCE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=8192,
    )
    result = _extract_text(response)
    logger.info(f"Claude 日報潤飾成功，回應長度: {len(result)}")
    return result


async def get_ai_enhanced_weekly_report(
    original_content: str,
    job_item: str,
    subject: str,
    reference_texts: List[str] = [],
) -> str:
    """使用 Claude 將週報內容潤飾成專業格式。"""
    logger.info(f"調用 Claude 潤飾週報，工作項目: {job_item}, 模型: {settings.CLAUDE_MODEL}")

    user_prompt = ai_prompts.build_weekly_enhance_user_prompt(
        job_item, subject, original_content, reference_texts
    )
    response = await _create_message(
        system=ai_prompts.WEEKLY_ENHANCE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=8192,
    )
    result = _extract_text(response)
    logger.info(f"Claude 週報潤飾成功，回應長度: {len(result)}")
    return result


async def generate_reply_suggestions(
    system_prompt: str,
    user_prompt: str,
) -> List[Dict[str, str]]:
    """
    生成主管回覆建議（結構化輸出，保證回傳合法 JSON）。

    Returns:
        [{"type": ..., "title": ..., "content": ...}, ...]
    """
    response = await _create_message(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=4096,
        output_schema=ai_prompts.SUGGESTION_OUTPUT_SCHEMA,
    )
    data = json.loads(_extract_text(response))
    suggestions = data.get("suggestions", [])
    logger.info(f"Claude 主管建議生成成功，數量: {len(suggestions)}")
    return suggestions


# 附件擷取支援的 MIME 類型（PDF 用 document block，其餘用 image block）
_IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


async def extract_text_from_document(
    data: bytes,
    media_type: str,
    file_name: str,
) -> str:
    """
    使用 Claude 視覺能力從 PDF / 圖片中擷取文字。

    Args:
        data: 檔案原始 bytes
        media_type: application/pdf 或 image/jpeg|png|gif|webp
        file_name: 檔案名稱（僅用於記錄）

    Returns:
        擷取的純文字內容
    """
    if media_type != "application/pdf" and media_type not in _IMAGE_MEDIA_TYPES:
        raise ClaudeServiceError(f"不支援的擷取格式: {media_type} ({file_name})")

    encoded = base64.standard_b64encode(data).decode("utf-8")
    if media_type == "application/pdf":
        source_block: Dict[str, Any] = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }
    else:
        source_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }

    logger.info(f"調用 Claude 擷取文件文字: {file_name} ({media_type}, {len(data)} bytes)")
    response = await _create_message(
        messages=[
            {
                "role": "user",
                "content": [
                    source_block,
                    {"type": "text", "text": ai_prompts.DOCUMENT_EXTRACT_PROMPT},
                ],
            }
        ],
        max_tokens=8000,  # 下游會截斷到 10000 字，無需更長輸出
        effort="low",  # 機械式擷取任務，降低思考深度以縮短延遲
        timeout=180.0,  # 多頁 PDF 的視覺轉錄可能超過一般呼叫的 60 秒
    )
    return _extract_text(response)
