// frontend/src/types/supervisor.ts
// Centralized type definitions to avoid duplication

export interface SupervisorApprovalInfo {
  supervisor_id: number;
  supervisor_name: string;
  supervisor_empno: string;
  status: "pending" | "approved";
  approved_at?: string;
  rating?: number;
  feedback?: string;
}

export interface ReportWithApprovals {
  approvals?: SupervisorApprovalInfo[];
  // This interface can be extended with other report properties as needed
}