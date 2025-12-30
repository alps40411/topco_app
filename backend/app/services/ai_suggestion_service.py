# backend/app/services/ai_suggestion_service.py

import json
from typing import List, Dict, Any
from app.services import azure_ai_service

async def generate_supervisor_reply_suggestions(
    report_content: str,
    employee_name: str,
    rating: int = None,
    recent_context: str = None
) -> List[Dict[str, str]]:
    """
    生成主管回覆建議選項

    Args:
        report_content: 當前日報內容
        employee_name: 員工姓名
        rating: 主管評分（1-5星），影響建議的語氣和內容
        recent_context: 最近兩天的報告摘要（可選）

    Returns:
        包含多個回覆選項的列表
    """

    # 根據評分決定語氣和風格
    rating_guidance = ""
    if rating == 5:
        rating_guidance = (
            "**評分：5星（優秀）**\n"
            "- 語氣：非常正向、肯定、鼓勵\n"
            "- 重點：充分肯定工作成果，鼓勵保持\n"
            "- 建議類型：肯定鼓勵、繼續保持、樹立典範\n"
        )
    elif rating == 4:
        rating_guidance = (
            "**評分：4星（良好）**\n"
            "- 語氣：正向肯定，略帶建議\n"
            "- 重點：肯定主要成果，提出小幅改進方向\n"
            "- 建議類型：肯定鼓勵、優化建議、持續進步\n"
        )
    elif rating == 3:
        rating_guidance = (
            "**評分：3星（普通）**\n"
            "- 語氣：中性客觀，平衡指出優缺點\n"
            "- 重點：認可努力，明確指出需改進之處\n"
            "- 建議類型：基本肯定、具體改進、期待提升\n"
        )
    elif rating == 2:
        rating_guidance = (
            "**評分：2星（待改進）**\n"
            "- 語氣：嚴肅但建設性，明確指出問題\n"
            "- 重點：指出明顯不足，要求具體改善\n"
            "- 建議類型：指出問題、改進要求、提供協助\n"
        )
    elif rating == 1:
        rating_guidance = (
            "**評分：1星（不及格）**\n"
            "- 語氣：嚴肅、直接，要求立即改善\n"
            "- 重點：明確指出嚴重問題，要求立即改正\n"
            "- 建議類型：嚴重問題、立即改善、警告提醒\n"
        )
    else:
        # 沒有評分時，使用中性語氣
        rating_guidance = (
            "**未提供評分**\n"
            "- 語氣：專業中性，平衡肯定與建議\n"
            "- 建議類型：肯定鼓勵、指導建議、關心支持\n"
        )

    system_prompt = (
    "你是一位專業、經驗豐富的部門主管。\n"
    "你的任務是根據員工的日報內容和主管評分，生成3個符合評分等級的專業回覆建議。\n\n"
    f"{rating_guidance}\n"
    "你必須嚴格遵守以下原則：\n\n"
    "1. **評分一致性原則**:\n"
    "   - 建議的語氣和內容必須與評分等級相符\n"
    "   - 高評分應正向鼓勵，低評分應嚴肅指出問題\n\n"
    "2. **內容導向原則**:\n"
    "   - 建議必須基於員工實際的工作內容\n"
    "   - 針對具體的工作成果或問題給出回饋\n\n"
    "3. **精選化原則**:\n"
    "   - 提供3種不同重點的建議\n"
    "   - 每個建議都要有不同的著重點\n\n"
    "4. **專業性與精簡原則**:\n"
    "   - 語言要專業、具體、有建設性\n"
    "   - **長度精簡（約30-50字）**\n"
    "   - 避免空泛的客套話\n\n"
    "5. **格式原則**:\n"
    "   - 必須回傳標準JSON格式\n"
    "   - 不得包含任何JSON之外的文字\n"
)
    

    user_prompt = f"""請為員工「{employee_name}」的以下日報內容生成專業的主管回覆建議：

<REPORT_CONTENT>
{report_content}
</REPORT_CONTENT>"""

    if rating:
        user_prompt += f"""

<RATING>
主管評分：{rating}星（共5星）
</RATING>"""

    if recent_context:
        user_prompt += f"""

<RECENT_CONTEXT>
{recent_context}
</RECENT_CONTEXT>"""

    # 根據評分調整建議類型範例
    if rating and rating <= 2:
        # 低評分：問題導向
        example_types = [
            {"type": "problem_identification", "title": "問題指出", "content": "明確指出工作中的問題"},
            {"type": "improvement_requirement", "title": "改進要求", "content": "具體的改進要求和期望"},
            {"type": "support_offer", "title": "協助提供", "content": "提供必要的協助和資源"}
        ]
    elif rating and rating == 3:
        # 中等評分：平衡
        example_types = [
            {"type": "basic_recognition", "title": "基本肯定", "content": "認可基本的工作努力"},
            {"type": "specific_improvement", "title": "具體改進", "content": "明確指出需要改進的地方"},
            {"type": "expectation", "title": "期待提升", "content": "期待未來的表現提升"}
        ]
    else:
        # 高評分或無評分：正向為主
        example_types = [
            {"type": "encouraging", "title": "肯定鼓勵", "content": "具體的肯定與鼓勵內容"},
            {"type": "guidance", "title": "指導建議", "content": "具體的指導與建議內容"},
            {"type": "inquiry_and_support", "title": "關心支持", "content": "具體的關心與支持內容"}
        ]

    user_prompt += f"""

請回傳以下JSON格式，不要包含任何其他文字：

{{
  "suggestions": {json.dumps(example_types, ensure_ascii=False, indent=4)}
}}

注意：建議的 type 和 title 可以根據評分調整，但必須符合評分等級的語氣要求。"""

    try:
        # 使用與 get_ai_enhanced_report 相同的方式調用 Azure AI
        client = azure_ai_service._build_client()
        if client is None:
            return _get_intelligent_suggestions(report_content, employee_name, rating)

        from app.core.config import settings
        
        response = await client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1,
            max_completion_tokens=1200,
        )
        ai_response = response.choices[0].message.content
        if not ai_response:
            return _get_intelligent_suggestions(report_content, employee_name, rating)

        # 嘗試解析 JSON 回應
        try:
            response_data = json.loads(ai_response)
            suggestions = response_data.get("suggestions", [])

            # 驗證回應格式
            if not suggestions or len(suggestions) == 0:
                return _get_intelligent_suggestions(report_content, employee_name, rating)

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
                return _get_intelligent_suggestions(report_content, employee_name, rating)

        except json.JSONDecodeError:
            return _get_intelligent_suggestions(report_content, employee_name, rating)

    except Exception:
        return _get_intelligent_suggestions(report_content, employee_name, rating)


def _get_intelligent_suggestions(report_content: str, employee_name: str, rating: int = None) -> List[Dict[str, str]]:
    """
    基於報告內容和評分生成智能建議（規則式方法）
    """
    # 分析報告內容的關鍵詞
    content_lower = report_content.lower()

    suggestions = []

    # 根據評分決定建議風格
    if rating == 1:
        # 1星：嚴重問題
        suggestions.append({
            "type": "serious_problem",
            "title": "嚴重問題",
            "content": f"{employee_name}的工作內容明顯不足，需要立即改善工作態度和執行品質。"
        })
        suggestions.append({
            "type": "immediate_improvement",
            "title": "立即改善",
            "content": "請在三天內提出具體的改善計畫，並與主管討論如何提升工作表現。"
        })
        suggestions.append({
            "type": "warning",
            "title": "警告提醒",
            "content": "若持續未達標準，將影響績效考核，請務必正視此問題。"
        })
    elif rating == 2:
        # 2星：需要改進
        suggestions.append({
            "type": "problem_identification",
            "title": "問題指出",
            "content": f"{employee_name}的工作執行不夠確實，報告內容缺乏深度和完整性。"
        })
        suggestions.append({
            "type": "improvement_requirement",
            "title": "改進要求",
            "content": "請加強工作細節的追蹤和記錄，確保每項任務都能完整執行。"
        })
        suggestions.append({
            "type": "support_offer",
            "title": "協助提供",
            "content": "如果在工作執行上遇到困難，請主動尋求協助，不要等到問題累積。"
        })
    elif rating == 3:
        # 3星：普通
        suggestions.append({
            "type": "basic_recognition",
            "title": "基本肯定",
            "content": f"{employee_name}的工作基本達標，但還有進步空間。"
        })
        suggestions.append({
            "type": "specific_improvement",
            "title": "具體改進",
            "content": "建議在工作規劃和時間管理上再加強，提升執行效率。"
        })
        suggestions.append({
            "type": "expectation",
            "title": "期待提升",
            "content": "期待下次能看到更深入的工作成果和更完整的報告內容。"
        })
    elif rating == 4:
        # 4星：良好
        if any(word in content_lower for word in ['完成', '修正', '優化', '實現', '成功']):
            suggestions.append({
                "type": "encouraging",
                "title": "肯定鼓勵",
                "content": f"{employee_name}的工作執行得很好，成果符合預期，請保持。"
            })
        else:
            suggestions.append({
                "type": "encouraging",
                "title": "肯定鼓勵",
                "content": f"{employee_name}的工作態度積極，表現良好。"
            })
        suggestions.append({
            "type": "optimization",
            "title": "優化建議",
            "content": "可以嘗試在工作方法上做些優化，提升效率和品質。"
        })
        suggestions.append({
            "type": "continuous_improvement",
            "title": "持續進步",
            "content": "持續保持這樣的工作品質，相信能達到更高的標準。"
        })
    else:
        # 5星或無評分：優秀
        if any(word in content_lower for word in ['完成', '修正', '優化', '實現', '成功']):
            suggestions.append({
                "type": "encouraging",
                "title": "肯定鼓勵",
                "content": f"{employee_name}的工作執行得非常出色，充分展現專業能力和責任感。"
            })
        else:
            suggestions.append({
                "type": "encouraging",
                "title": "肯定鼓勵",
                "content": f"{employee_name}的工作態度和表現都很優秀，值得肯定。"
            })

        if any(word in content_lower for word in ['bug', '錯誤', '問題', '修復']):
            suggestions.append({
                "type": "guidance",
                "title": "繼續保持",
                "content": "在問題處理上表現專業，建議持續累積這方面的經驗。"
            })
        else:
            suggestions.append({
                "type": "guidance",
                "title": "繼續保持",
                "content": "工作內容完整且具體，請繼續保持這樣的高水準。"
            })

        suggestions.append({
            "type": "role_model",
            "title": "樹立典範",
            "content": "您的工作表現可以作為團隊的標竿，值得其他同仁學習。"
        })

    return suggestions

def _get_fallback_suggestions() -> List[Dict[str, str]]:
    """
    當所有方法都失敗時的最基本建議選項
    """
    return [
        {
            "type": "encouraging",
            "title": "肯定鼓勵",
            "content": "工作內容詳實，執行效果良好，請繼續保持這樣的工作節奏。"
        },
        {
            "type": "guidance",
            "title": "指導建議", 
            "content": "報告內容完整，建議在執行細節上可以更加具體，有助於後續追蹤。"
        },
        {
            "type": "inquiry_and_support",
            "title": "關心支持",
            "content": "工作進度符合預期，如果在執行過程中遇到任何困難，請隨時討論。"
        }
    ]