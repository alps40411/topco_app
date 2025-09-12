# backend/app/services/azure_ai_service.py
from openai import AsyncAzureOpenAI
from app.core.config import settings
from typing import List, Optional
import aiofiles
import aiohttp
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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
    print("User Prompt:", user_prompt)  # Debugging line to check the prompt content
    client = _build_client()
    if client is None:
        return "AI service not available."
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
        return ai_content if ai_content else "Unable to get content from AI service."
    except Exception as e:
        return "AI service temporarily unavailable."

async def get_completion(prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> str:
    """
    使用 Azure OpenAI 獲取通用文本完成回應
    """
    client = _build_client()
    if client is None:
        raise Exception("AI service not configured")
    
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
        
        return ai_content if ai_content else "Unable to get content from AI service"
    except Exception as e:
        error_msg = f"Azure AI API error: {str(e)}"
        print(error_msg)
        raise Exception("AI service call failed")

async def extract_text_from_file(file_path: str) -> str:
    """
    使用 Azure Document Intelligence 從檔案中提取文字內容
    """
    logger.info(f"開始提取檔案內容: {file_path}")
    
    # 檢查配置
    if not settings.AZURE_DOC_INTELLIGENCE_KEY or not settings.AZURE_DOC_INTELLIGENCE_ENDPOINT:
        logger.warning("Azure Document Intelligence 未配置，跳過檔案內容提取")
        logger.warning(f"Key存在: {bool(settings.AZURE_DOC_INTELLIGENCE_KEY)}")
        logger.warning(f"Endpoint存在: {bool(settings.AZURE_DOC_INTELLIGENCE_ENDPOINT)}")
        return ""
    
    logger.info(f"Azure Document Intelligence 已配置")
    
    try:
        # 檢查檔案是否存在
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.error(f"檔案不存在: {file_path}")
            return ""
        
        logger.info(f"檔案存在: {file_path}")
        
        # 檢查檔案類型
        file_ext = file_path_obj.suffix.lower()
        logger.info(f"檔案類型: {file_ext}")
        
        supported_types = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
        if file_ext not in supported_types:
            logger.info(f"檔案類型 {file_ext} 不支援 Document Intelligence，嘗試讀取為純文字")
            # 嘗試讀取純文字檔案
            if file_ext in {'.txt', '.md', '.csv'}:
                try:
                    logger.info(f"嘗試以UTF-8讀取純文字檔案")
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        logger.info(f"成功讀取純文字檔案: {len(content)} 字符")
                        return content[:10000]  # 限制長度
                except UnicodeDecodeError:
                    try:
                        logger.info(f"UTF-8失敗，嘗試以Big5讀取")
                        async with aiofiles.open(file_path, 'r', encoding='big5') as f:
                            content = await f.read()
                            logger.info(f"以Big5成功讀取純文字檔案: {len(content)} 字符")
                            return content[:10000]
                    except Exception as e:
                        logger.error(f"Big5讀取也失敗: {str(e)}")
                        return ""
                except Exception as e:
                    logger.error(f"讀取純文字檔案失敗: {str(e)}")
                    return ""
            else:
                logger.warning(f"不支援的檔案類型: {file_ext}")
            return ""
        
        # 準備 API 請求
        logger.info(f"開始調用 Azure Document Intelligence API")
        endpoint_url = f"{settings.AZURE_DOC_INTELLIGENCE_ENDPOINT}/formrecognizer/documentModels/prebuilt-read:analyze"
        logger.info(f"API 端點: {endpoint_url}")
        
        headers = {
            "Ocp-Apim-Subscription-Key": settings.AZURE_DOC_INTELLIGENCE_KEY,
            "Content-Type": "application/octet-stream"
        }
        params = {
            "api-version": "2023-07-31"
        }
        
        # 讀取檔案內容
        logger.info(f"讀取檔案內容...")
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            logger.info(f"檔案讀取成功: {len(file_content)} 位元組")
        except Exception as e:
            logger.error(f"檔案讀取失敗: {str(e)}")
            return ""
        
        # 發送分析請求
        logger.info(f"發送 Document Intelligence 分析請求...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint_url,
                    headers=headers,
                    params=params,
                    data=file_content
                ) as response:
                    logger.info(f"API 響應狀態: {response.status}")
                    
                    if response.status != 202:
                        response_text = await response.text()
                        logger.error(f"Document Intelligence 分析請求失敗: {response.status}")
                        logger.error(f"響應內容: {response_text}")
                        return ""
                    
                    # 取得分析結果的URL
                    operation_location = response.headers.get('Operation-Location')
                    if not operation_location:
                        logger.error("無法取得分析結果URL")
                        return ""
                    
                    logger.info(f"分析請求成功，結果URL: {operation_location}")
        except Exception as e:
            logger.error(f"發送API請求失敗: {str(e)}")
            return ""
        
        # 等待分析完成並取得結果
        result_headers = {
            "Ocp-Apim-Subscription-Key": settings.AZURE_DOC_INTELLIGENCE_KEY
        }
        
        logger.info(f"開始輪詢分析結果...")
        try:
            async with aiohttp.ClientSession() as session:
                # 輪詢分析結果（最多等待30秒）
                import asyncio
                for attempt in range(30):
                    await asyncio.sleep(1)  # 等待1秒
                    
                    logger.info(f"輪詢嘗試 {attempt + 1}/30")
                    
                    async with session.get(operation_location, headers=result_headers) as result_response:
                        logger.info(f"輪詢響應狀態: {result_response.status}")
                        
                        if result_response.status != 200:
                            logger.warning(f"輪詢失敗，狀態碼: {result_response.status}")
                            continue
                        
                        result_data = await result_response.json()
                        status = result_data.get('status')
                        logger.info(f"分析狀態: {status}")
                        
                        if status == 'succeeded':
                            logger.info(f"Document Intelligence 分析成功！")
                            # 提取文字內容
                            content_parts = []
                            if 'analyzeResult' in result_data and 'content' in result_data['analyzeResult']:
                                content_parts.append(result_data['analyzeResult']['content'])
                                logger.info(f"找到分析結果內容")
                            else:
                                logger.warning(f"分析結果中沒有找到content")
                                logger.info(f"結果數據鍵: {list(result_data.keys())}")
                            
                            extracted_text = '\n'.join(content_parts)
                            logger.info(f"成功從檔案 {file_path} 提取了 {len(extracted_text)} 個字符")
                            return extracted_text[:10000]  # 限制長度避免token超限
                        
                        elif status == 'failed':
                            logger.error(f"Document Intelligence 分析失敗: {result_data}")
                            return ""
                        elif status in ['notStarted', 'running']:
                            logger.info(f"分析仍在進行中: {status}")
                        else:
                            logger.warning(f"未知狀態: {status}")
                
                logger.warning("Document Intelligence 分析超時")
                return ""
        except Exception as e:
            logger.error(f"輪詢過程發生錯誤: {str(e)}")
            return ""
    
    except Exception as e:
        logger.error(f"檔案內容提取失敗 {file_path}: {str(e)}")
        return ""

async def process_attachments_for_ai(attachment_records: List[dict]) -> List[str]:
    """
    處理附件列表，提取標記為 AI 參考的檔案內容
    """
    reference_texts = []
    
    logger.info(f"開始處理附件，總數: {len(attachment_records)}")
    
    for attachment in attachment_records:
        logger.info(f"檢查附件: {attachment}")
        
        if not attachment.get('is_selected_for_ai', False):
            logger.info(f"附件 {attachment.get('file_name', '未知')} 未標記為AI參考，跳過")
            continue
        
        file_path = attachment.get('file_path')
        file_name = attachment.get('file_name', '未知檔案')
        
        if not file_path:
            logger.warning(f"附件 {file_name} 沒有檔案路徑")
            continue
        
        logger.info(f"開始處理AI參考檔案: {file_name} (路徑: {file_path})")
        
        try:
            extracted_text = await extract_text_from_file(file_path)
            
            if extracted_text:
                # 添加檔案來源標識
                formatted_text = f"【檔案：{file_name}】\n{extracted_text}"
                reference_texts.append(formatted_text)
                logger.info(f"成功提取檔案內容: {file_name} ({len(extracted_text)} 字符)")
            else:
                logger.warning(f"無法提取檔案內容: {file_name}")
        except Exception as e:
            logger.error(f"處理檔案 {file_name} 時發生錯誤: {str(e)}")
    
    logger.info(f"附件處理完成，成功提取 {len(reference_texts)} 個檔案內容")
    return reference_texts