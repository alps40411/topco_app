// frontend/src/services/types/user.ts
/**
 * 用戶相關型別定義
 */

export interface UserProfile {
  id: string;
  username: string;
  email?: string;
  employee?: EmployeeInfo;
}

export interface EmployeeInfo {
  empno: string;
  empnamec: string;
  cocode: string;
  deptno: string;
  deptnamec?: string;
  g_deptno?: string;
  leader?: string;
}

export interface UserPermissions {
  is_supervisor: boolean;
  has_subordinates: boolean;
  can_approve: boolean;
  can_forward: boolean;
}

export interface Subordinate {
  empno: string;
  empnamec: string;
  cocode: string;
  deptno: string;
  deptnamec?: string;
}
