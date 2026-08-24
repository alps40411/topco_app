# backend/app/services/ai_suggestion_service.py

import logging
from typing import List, Dict

from app.services import ai_prompts, claude_ai_service

logger = logging.getLogger(__name__)


async def generate_supervisor_reply_suggestions(
    report_content: str,
    employee_name: str,
    rating: int = None,
    recent_context: str = None
) -> List[Dict[str, str]]:
    """
    生成主管回覆建議選項

    使用 Claude 結構化輸出保證回傳合法 JSON；
    AI 服務不可用時降級為規則式建議。

    Args:
        report_content: 當前日報內容
        employee_name: 員工姓名
        rating: 主管評分（1-5星），影響建議的語氣和內容
        recent_context: 最近兩天的報告摘要（可選）

    Returns:
        包含多個回覆選項的列表
    """
    system_prompt = ai_prompts.build_suggestion_system_prompt(rating)
    user_prompt = ai_prompts.build_suggestion_user_prompt(
        report_content=report_content,
        employee_name=employee_name,
        rating=rating,
        recent_context=recent_context,
    )

    try:
        suggestions = await claude_ai_service.generate_reply_suggestions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # 結構化輸出已保證欄位齊全，這裡僅防禦空結果
        valid_suggestions = [
            s for s in suggestions
            if isinstance(s, dict) and s.get("type") and s.get("title") and s.get("content")
        ]
        if valid_suggestions:
            return valid_suggestions

        logger.warning("Claude 回傳的建議列表為空，改用規則式建議")
        return _get_intelligent_suggestions(report_content, employee_name, rating)

    except Exception as e:
        logger.error(f"AI 建議生成失敗，改用規則式建議: {str(e)}")
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
