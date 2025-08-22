# backend/app/services/ai_suggestion_service.py

import json
from typing import List, Dict, Any
from app.services import azure_ai_service

async def generate_supervisor_reply_suggestions(
    report_content: str, 
    employee_name: str, 
    recent_context: str = None
) -> List[Dict[str, str]]:
    """
    生成主管回覆建議選項
    
    Args:
        report_content: 當前日報內容
        employee_name: 員工姓名
        recent_context: 最近兩天的報告摘要（可選）
    
    Returns:
        包含多個回覆選項的列表
    """
    
    system_prompt = (
    "你是一位專業、經驗豐富的部門主管。\n"
    "你的任務是根據員工的日報內容，生成3個不同風格和重點的專業回覆建議。\n\n"
    "你必須嚴格遵守以下原則：\n\n"
    "1. **內容導向原則**:\n"
    "   - 建議必須基於員工實際的工作內容\n"
    "   - 針對具體的工作成果或問題給出回饋\n\n"
    "2. **精選化原則**:\n"
    "   - 提供3種精選風格的建議：肯定鼓勵、指導建議、關心支持\n"
    "   - 每個建議都要有不同的重點和語調\n\n"
    "3. **專業性與精簡原則**:\n"
    "   - 語言要專業、具體、有建設性\n"
    "   - **長度精簡（約30-50字）**\n"
    "   - 避免空泛的客套話\n\n"
    "4. **格式原則**:\n"
    "   - 必須回傳標準JSON格式\n"
    "   - 不得包含任何JSON之外的文字\n"
)
    

    user_prompt = f"""請為員工「{employee_name}」的以下日報內容生成專業的主管回覆建議：

<REPORT_CONTENT>
{report_content}
</REPORT_CONTENT>"""

    if recent_context:
        user_prompt += f"""

<RECENT_CONTEXT>
{recent_context}
</RECENT_CONTEXT>"""

    user_prompt += """

請回傳以下JSON格式，不要包含任何其他文字：

{
  "suggestions": [
    {
      "type": "encouraging",
      "title": "肯定鼓勵",
      "content": "具體的肯定與鼓勵內容"
    },
    {
      "type": "guidance",
      "title": "指導建議",
      "content": "具體的指導與建議內容"
    },
    {
      "type": "inquiry_and_support",
      "title": "關心支持",
      "content": "具體的關心與支持內容"
    }
  ]
}"""

    try:
        # 使用與 get_ai_enhanced_report 相同的方式調用 Azure AI
        client = azure_ai_service._build_client()
        if client is None:
            return _get_intelligent_suggestions(report_content, employee_name)

        from app.core.config import settings
        
        response = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        ai_response = response.choices[0].message.content
        if not ai_response:
            return _get_intelligent_suggestions(report_content, employee_name)
        
        # 嘗試解析 JSON 回應
        try:
            response_data = json.loads(ai_response)
            suggestions = response_data.get("suggestions", [])
            
            # 驗證回應格式
            if not suggestions or len(suggestions) == 0:
                return _get_intelligent_suggestions(report_content, employee_name)
            
            # 驗證每個建議的格式
            valid_suggestions = []
            for suggestion in suggestions:
                if (isinstance(suggestion, dict) and 
                    'type' in suggestion and 
                    'title' in suggestion and 
                    'content' in suggestion):
                    valid_suggestions.append(suggestion)
                    
            if valid_suggestions:
                return valid_suggestions
            else:
                return _get_intelligent_suggestions(report_content, employee_name)
            
        except json.JSONDecodeError:
            return _get_intelligent_suggestions(report_content, employee_name)
            
    except Exception:
        return _get_intelligent_suggestions(report_content, employee_name)


def _get_intelligent_suggestions(report_content: str, employee_name: str) -> List[Dict[str, str]]:
    """
    基於報告內容生成智能建議（規則式方法）
    """
    # 分析報告內容的關鍵詞
    content_lower = report_content.lower()
    
    suggestions = []
    
    # 鼓勵肯定建議
    if any(word in content_lower for word in ['完成', '修正', '優化', '實現', '成功']):
        suggestions.append({
            "type": "encouraging",
            "title": "鼓勵肯定",
            "content": f"{employee_name}的工作執行得很完整，展現出良好的技術能力和工作態度，請保持這樣的工作品質。"
        })
    else:
        suggestions.append({
            "type": "encouraging",
            "title": "鼓勵肯定",
            "content": f"{employee_name}的工作態度認真，請繼續保持積極的工作動力。"
        })
    
    # 指導建議
    if any(word in content_lower for word in ['bug', '錯誤', '問題', '修復']):
        suggestions.append({
            "type": "guidance",
            "title": "指導建議",
            "content": "在問題處理上表現不錯，建議可以記錄問題發生的原因和解決方法，有助於經驗累積。"
        })
    else:
        suggestions.append({
            "type": "guidance",
            "title": "指導建議",
            "content": "報告內容完整，建議在執行細節上可以更具體，有助於後續工作追蹤。"
        })
    
    # 關心詢問
    if any(word in content_lower for word in ['困難', '阻礙', '延遲', '等待']):
        suggestions.append({
            "type": "inquiry",
            "title": "關心詢問",
            "content": "注意到工作中遇到一些挑戰，如果需要協助或資源支持，請隨時討論。"
        })
    else:
        suggestions.append({
            "type": "inquiry",
            "title": "關心詢問",
            "content": "工作進度看起來順利，如果在執行過程中有任何疑問，歡迎隨時交流。"
        })
    
    # 改進建議
    if any(word in content_lower for word in ['測試', '驗證', '檢查']):
        suggestions.append({
            "type": "suggestion",
            "title": "改進建議",
            "content": "在品質管控方面表現良好，建議可以建立更系統化的測試流程。"
        })
    else:
        suggestions.append({
            "type": "suggestion",
            "title": "改進建議",
            "content": "整體表現良好，建議加強時程規劃，可進一步提升工作效率。"
        })
    
    # 協作支持
    if any(word in content_lower for word in ['協作', '討論', '會議', '溝通']):
        suggestions.append({
            "type": "collaborative",
            "title": "協作支持",
            "content": "團隊協作意識很好，未來有跨部門合作需求時，我會提供必要的支援。"
        })
    else:
        suggestions.append({
            "type": "collaborative",
            "title": "協作支持",
            "content": "如果在工作過程中需要額外資源或其他部門協助，請主動提出需求。"
        })
    
    return suggestions

def _get_fallback_suggestions() -> List[Dict[str, str]]:
    """
    當所有方法都失敗時的最基本建議選項
    """
    return [
        {
            "type": "encouraging",
            "title": "鼓勵肯定",
            "content": "工作內容詳實，執行效果良好，請繼續保持這樣的工作節奏。"
        },
        {
            "type": "guidance",
            "title": "指導建議", 
            "content": "報告內容完整，建議在執行細節上可以更加具體，有助於後續追蹤。"
        },
        {
            "type": "inquiry",
            "title": "關心詢問",
            "content": "工作進度符合預期，如果在執行過程中遇到任何困難，請隨時討論。"
        },
        {
            "type": "suggestion",
            "title": "改進建議",
            "content": "整體表現良好，建議在時程管控上可以更加精確，以提升效率。"
        },
        {
            "type": "collaborative", 
            "title": "協作支持",
            "content": "看起來進展順利，如需要額外資源或協助，請主動提出需求。"
        }
    ]