# backend/app/services/azure_ai_service.py
from openai import AsyncAzureOpenAI
from app.core.config import settings
from typing import List, Optional

def _build_client() -> Optional[AsyncAzureOpenAI]:
    if not settings.AZURE_OPENAI_KEY or not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_DEPLOYMENT_NAME:
        return None
    
    return AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_KEY,
        api_version="2024-02-01",
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )

async def get_ai_enhanced_report(original_content: str, project_name: str, reference_texts: List[str] = []) -> str:
    """
    使用 Azure OpenAI 將報告內容潤飾成專業格式，並參考附加文件內容。
    """
    system_prompt = (
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
        "   - 如果筆記中未提及任何問題，你必須在該部分註明「**目前無明顯阻礙。**」，絕不允許臆測或編造問題。\n\n"
        "--- 範例 --- \n\n"
        "<EXAMPLE>\n"
        "INPUT:\n"
        "<NOTES>\n"
        "修改前端程式，完成後端auth驗證\n"
        "</NOTES>\n\n"
        "OUTPUT:\n"
        "一、今日進度\n\n"
        "對前端應用程式進行了修改。\n"
        "完成了後端的身份驗證功能，為系統安全性奠定基礎。\n\n"
        "二、明日計畫\n\n"
        "待下一步規劃。\n\n"
        "三、潛在問題與阻礙\n\n"
        "目前無明顯阻礙。\n"
        "</EXAMPLE>\n\n"
    )
    reference_section = ""
    if reference_texts:
        combined_references = "\n\n".join(reference_texts)
        reference_section = f"\n\n<REFERENCES>\n{combined_references}\n</REFERENCES>"

    user_prompt = (
        f"請為「{project_name}」這個專案，潤飾以下工作內容，並參考附加的資料，生成一份每日工作報告。\n\n"
        # 使用標籤來界定筆記
        f"<NOTES>\n{original_content}\n</NOTES>"
        f"{reference_section}"
    )

    client = _build_client()
    if client is None:
        return "AI 服務未啟用或尚未配置。"
    try:
        response = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        ai_content = response.choices[0].message.content
        return ai_content if ai_content else "無法從 AI 服務獲取內容。"
    except Exception as e:
        return "AI 服務暫時無法使用。"

async def get_completion(prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
    """
    使用 Azure OpenAI 獲取通用文本完成回應
    """
    client = _build_client()
    if client is None:
        raise Exception("AI 服務未啟用或尚未配置")
    
    try:
        response = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        ai_content = response.choices[0].message.content
        
        return ai_content if ai_content else "無法從 AI 服務獲取內容"
    except Exception as e:
        error_msg = f"Azure AI API error: {str(e)}"
        print(error_msg)
        raise Exception(f"AI 服務調用失敗: {str(e)}")