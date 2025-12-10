# backend/app/services/work_data_service.py

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class WorkDataService:
    """處理工作相關資料的服務 - 專案、執行工作、工作項目、服務對象等"""

    @staticmethod
    def get_all_work_data(
        db: Session,
        empno: str,
        cocode: str
    ) -> Dict[str, Any]:
        """
        一次性獲取填寫日報所需的所有工作資料
        包含：專案列表、執行工作、服務公司、服務對象
        """
        try:
            result = {
                "projects": [],
                "execution_works": [],
                "service_companies": [],
                "service_targets": []
            }

            # 1. 查詢專案列表（與舊 API 相同的查詢）
            projects_sql = text("""
                SELECT DISTINCT A.planno, A.plan_subj_c
                FROM jps.tjp_master A
                LEFT JOIN jps.tjp_partner E ON A.planno = E.planno
                WHERE (A.empno = :empno OR A.pm_empno = :empno OR E.part_empno = :empno)
                AND (A.plan_date2 IS NULL OR A.plan_date2 >= TO_CHAR(CURRENT_DATE,'YYYYMMDD'))
                AND A.status IS NULL
                ORDER BY A.planno DESC
            """)
            projects = db.execute(projects_sql, {"empno": empno}).fetchall()
            result["projects"] = [
                {
                    "id": p[0],
                    "planno": p[0],
                    "plan_subj_c": p[1] or f"工作計畫 {p[0]}"
                }
                for p in projects
            ]

            # 2. 查詢基本執行工作（沒有專案關聯的執行工作）
            basic_exec_works_sql = text("""
                SELECT A.sopno, A.sop_desc_c, B.seq, B.name
                FROM (
                    SELECT sopno, sop_desc_c
                    FROM jps.tpm_sop
                    WHERE cocode IN ('A','E','H','M','K','P','L','R','G','J07','J09','J10','J11','S','J15','J16','J17','J18','J19')
                    AND xstatus = '1'
                    AND (deptno IS NULL OR deptno = '00253')
                    AND (sop_role IS NULL OR sop_role = '技術同仁')
                ) A
                LEFT JOIN jps.tpm_sop_detail B ON A.sopno = B.sopno
                ORDER BY A.sopno, B.seq
            """)

            basic_exec_result = db.execute(basic_exec_works_sql).fetchall()

            # 將基本執行工作組織成包含 work_items 的結構
            basic_execution_works = []
            current_sop = None

            for row in basic_exec_result:
                sopno = row[0]
                sop_desc_c = row[1]
                seq = row[2] if len(row) > 2 else None
                work_item_name = row[3] if len(row) > 3 else None

                if current_sop != sopno:
                    basic_execution_works.append({
                        "sopno": str(sopno),
                        "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                        "work_items": []
                    })
                    current_sop = sopno

                if seq is not None and work_item_name:
                    basic_execution_works[-1]["work_items"].append({
                        "seq": str(seq),
                        "name": work_item_name,
                        "unique_id": f"{sopno}_{seq}"
                    })

            result["basic_execution_works"] = basic_execution_works
            result["execution_works"] = basic_execution_works  # 向後兼容

            # 2.5 查詢專案與執行工作的關聯
            project_exec_works_sql = text("""
                SELECT t.planno, s.sopno, s.sop_desc_c, d.seq, d.name
                FROM jps.tjp_master t
                JOIN jps.tpm_sop s ON t.sopno = s.sopno
                LEFT JOIN jps.tpm_sop_detail d ON s.sopno = d.sopno
                WHERE t.empno = :empno OR t.pm_empno = :empno
                   OR t.planno IN (
                       SELECT planno FROM jps.tjp_partner WHERE part_empno = :empno
                   )
                ORDER BY t.planno, s.sopno, d.seq
            """)

            project_exec_result = db.execute(project_exec_works_sql, {"empno": empno}).fetchall()

            # 組織專案執行工作關聯: { planno: [execution_works] }
            project_execution_works = {}
            current_planno = None
            current_sop = None

            for row in project_exec_result:
                planno = str(row[0])
                sopno = row[1]
                sop_desc_c = row[2]
                seq = row[3] if len(row) > 3 else None
                work_item_name = row[4] if len(row) > 4 else None

                # 初始化專案的執行工作列表
                if planno not in project_execution_works:
                    project_execution_works[planno] = []

                # 如果是新的執行工作,添加到列表
                if current_planno != planno or current_sop != sopno:
                    project_execution_works[planno].append({
                        "sopno": str(sopno),
                        "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                        "work_items": []
                    })
                    current_planno = planno
                    current_sop = sopno

                # 添加工作項目
                if seq is not None and work_item_name:
                    project_execution_works[planno][-1]["work_items"].append({
                        "seq": str(seq),
                        "name": work_item_name,
                        "unique_id": f"{sopno}_{seq}"
                    })

            result["project_execution_works"] = project_execution_works

            # 3. 查詢服務公司列表（與舊 API 完全相同）
            service_companies_sql = text("SELECT cocode, coabbv FROM jps.dcd001$master WHERE eip_active = 'Y' order by cocode")
            service_companies_result = db.execute(service_companies_sql)
            service_companies = []
            for row in service_companies_result.fetchall():
                service_companies.append({
                    "id": row[0],  # cocode as id
                    "cocode": row[0],
                    "coabbv": row[1]
                })
            result["service_companies"] = service_companies

            # 4. 查詢服務對象列表（與舊 API 完全相同）
            service_targets_sql = text("""
                SELECT a.cocode, a.coabbv, b.deptno, b.deptabbv, c.empno, c.empnamec
                FROM jps.dcd001$master a
                JOIN jps.dcd002$master b ON b.cocode = a.cocode
                JOIN jps.dcd003$master c ON c.cocode = b.cocode
                AND c.deptno = b.deptno
                AND c.estatus <> '3'
                AND a.cocode NOT IN ('001')
                WHERE c.quitdate IS NULL
                ORDER BY a.cocode, b.deptno, c.empno
            """)
            service_targets_result = db.execute(service_targets_sql)
            service_targets = []
            for row in service_targets_result.fetchall():
                service_targets.append({
                    "cocode": row[0],
                    "coabbv": row[1],
                    "deptno": row[2],
                    "deptabbv": row[3],
                    "empno": row[4],
                    "empnamec": row[5]
                })
            result["service_targets"] = service_targets

            logger.info(
                f"工作資料查詢成功: empno={empno}, "
                f"專案={len(result['projects'])}, "
                f"基本執行工作={len(result['basic_execution_works'])}, "
                f"專案執行工作關聯={len(result['project_execution_works'])} 個專案, "
                f"服務公司={len(result['service_companies'])}, "
                f"服務對象={len(result['service_targets'])}"
            )

            return result

        except Exception as e:
            logger.error(f"Error getting work data: {str(e)}")
            raise

    @staticmethod
    def get_work_items_by_sopno(
        db: Session,
        sopno: str
    ) -> List[Dict[str, Any]]:
        """根據執行工作編號查詢工作項目"""
        try:
            sql = text("""
                SELECT seq, name
                FROM jps.tpm_sop_detail
                WHERE sopno = :sopno
                ORDER BY seq
            """)

            result = db.execute(sql, {"sopno": sopno}).fetchall()

            work_items = [
                {
                    "seq": w[0],
                    "name": w[1]
                }
                for w in result
            ]

            logger.info(f"查詢工作項目: sopno={sopno}, 項目數={len(work_items)}")
            return work_items

        except Exception as e:
            logger.error(f"Error getting work items: {str(e)}")
            raise
