import { api } from "@/lib/api";
import type {
  ActivityListResponse,
  ApprovalListResponse,
  ApprovalOut,
  BottleneckTask,
  DepartmentProductivity,
  MilestoneListResponse,
  MilestoneOut,
  SprintListResponse,
  SprintOut,
  TaskAnalyticsDashboard,
  TaskCommentOut,
  TaskDetailOut,
  TaskListResponse,
  TaskOut,
  TaskRecommendationListResponse,
  TaskRecommendationOut,
  TeamScore,
  UserWorkload,
} from "@/types";

// ── List / CRUD ───────────────────────────────────────────────────────────────

export async function listTasksApi(params?: {
  status?: string;
  assignee_id?: string;
  page?: number;
  size?: number;
}): Promise<TaskListResponse> {
  const r = await api.get<TaskListResponse>("/tasks", { params });
  return r.data;
}

export async function createTaskApi(body: {
  title: string;
  description?: string;
  priority?: string;
  task_type?: string;
  source?: string;
  departments?: string[];
  due_at?: string;
  sla_hours?: number;
  task_metadata?: Record<string, unknown>;
  assignee_ids?: string[];
}): Promise<TaskOut> {
  const r = await api.post<TaskOut>("/tasks", body);
  return r.data;
}

export async function getTaskApi(taskId: string): Promise<TaskDetailOut> {
  const r = await api.get<TaskDetailOut>(`/tasks/${taskId}`);
  return r.data;
}

export async function updateTaskApi(
  taskId: string,
  body: {
    title?: string;
    description?: string;
    priority?: string;
    task_type?: string;
    departments?: string[];
    due_at?: string;
    sla_hours?: number;
    task_metadata?: Record<string, unknown>;
  }
): Promise<TaskOut> {
  const r = await api.patch<TaskOut>(`/tasks/${taskId}`, body);
  return r.data;
}

export async function deleteTaskApi(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}`);
}

// ── Workflow ──────────────────────────────────────────────────────────────────

export async function transitionTaskApi(
  taskId: string,
  toStatus: string
): Promise<TaskOut> {
  const r = await api.post<TaskOut>(`/tasks/${taskId}/transition`, {
    to_status: toStatus,
  });
  return r.data;
}

// ── Assignees ─────────────────────────────────────────────────────────────────

export async function assignTaskApi(
  taskId: string,
  userId: string,
  roleInTask = "collaborator"
): Promise<TaskOut> {
  const r = await api.post<TaskOut>(`/tasks/${taskId}/assignees`, {
    user_id: userId,
    role_in_task: roleInTask,
  });
  return r.data;
}

export async function removeAssigneeApi(
  taskId: string,
  userId: string
): Promise<TaskOut> {
  const r = await api.delete<TaskOut>(`/tasks/${taskId}/assignees/${userId}`);
  return r.data;
}

// ── Comments ──────────────────────────────────────────────────────────────────

export async function addCommentApi(
  taskId: string,
  body: string
): Promise<TaskCommentOut> {
  const r = await api.post<TaskCommentOut>(`/tasks/${taskId}/comments`, { body });
  return r.data;
}

// ── Activity ──────────────────────────────────────────────────────────────────

export async function getActivityApi(
  taskId: string,
  page = 1,
  size = 25
): Promise<ActivityListResponse> {
  const r = await api.get<ActivityListResponse>(`/tasks/${taskId}/activity`, {
    params: { page, size },
  });
  return r.data;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export async function getAnalyticsDashboardApi(): Promise<TaskAnalyticsDashboard> {
  const r = await api.get<TaskAnalyticsDashboard>("/tasks/analytics/dashboard");
  return r.data;
}

export async function getDepartmentProductivityApi(): Promise<DepartmentProductivity[]> {
  const r = await api.get<DepartmentProductivity[]>("/tasks/analytics/department");
  return r.data;
}

export async function getWorkloadApi(): Promise<UserWorkload[]> {
  const r = await api.get<UserWorkload[]>("/tasks/analytics/workload");
  return r.data;
}

export async function getBottlenecksApi(params?: {
  stuck_hours?: number;
  limit?: number;
}): Promise<BottleneckTask[]> {
  const r = await api.get<BottleneckTask[]>("/tasks/analytics/bottlenecks", { params });
  return r.data;
}

export async function getTeamScoreApi(): Promise<TeamScore> {
  const r = await api.get<TeamScore>("/tasks/analytics/team-score");
  return r.data;
}

// ── Recommendations ───────────────────────────────────────────────────────────

export async function listRecommendationsApi(params?: {
  page?: number;
  size?: number;
}): Promise<TaskRecommendationListResponse> {
  const r = await api.get<TaskRecommendationListResponse>("/tasks/recommendations", { params });
  return r.data;
}

export async function refreshRecommendationsApi(): Promise<TaskRecommendationOut[]> {
  const r = await api.post<TaskRecommendationOut[]>("/tasks/recommendations/refresh");
  return r.data;
}

// ── Department board ──────────────────────────────────────────────────────────

export async function getDepartmentBoardApi(
  department: string,
  params?: { sprint_id?: string; page?: number; size?: number }
): Promise<TaskListResponse> {
  const r = await api.get<TaskListResponse>(`/tasks/board/${department}`, { params });
  return r.data;
}

// ── Milestones ────────────────────────────────────────────────────────────────

export async function listMilestonesApi(params?: {
  milestone_status?: string;
  page?: number;
  size?: number;
}): Promise<MilestoneListResponse> {
  const r = await api.get<MilestoneListResponse>("/tasks/milestones", { params });
  return r.data;
}

export async function createMilestoneApi(body: {
  name: string;
  description?: string;
  due_at?: string;
}): Promise<MilestoneOut> {
  const r = await api.post<MilestoneOut>("/tasks/milestones", body);
  return r.data;
}

export async function updateMilestoneApi(
  milestoneId: string,
  body: { name?: string; description?: string; due_at?: string; status?: string }
): Promise<MilestoneOut> {
  const r = await api.patch<MilestoneOut>(`/tasks/milestones/${milestoneId}`, body);
  return r.data;
}

export async function deleteMilestoneApi(milestoneId: string): Promise<void> {
  await api.delete(`/tasks/milestones/${milestoneId}`);
}

// ── Sprints ───────────────────────────────────────────────────────────────────

export async function listSprintsApi(params?: {
  sprint_status?: string;
  page?: number;
  size?: number;
}): Promise<SprintListResponse> {
  const r = await api.get<SprintListResponse>("/tasks/sprints", { params });
  return r.data;
}

export async function createSprintApi(body: {
  name: string;
  goal?: string;
  starts_at: string;
  ends_at: string;
  capacity_hours?: number;
}): Promise<SprintOut> {
  const r = await api.post<SprintOut>("/tasks/sprints", body);
  return r.data;
}

export async function getSprintApi(sprintId: string): Promise<SprintOut> {
  const r = await api.get<SprintOut>(`/tasks/sprints/${sprintId}`);
  return r.data;
}

export async function updateSprintApi(
  sprintId: string,
  body: { name?: string; goal?: string; starts_at?: string; ends_at?: string; status?: string; capacity_hours?: number }
): Promise<SprintOut> {
  const r = await api.patch<SprintOut>(`/tasks/sprints/${sprintId}`, body);
  return r.data;
}

export async function deleteSprintApi(sprintId: string): Promise<void> {
  await api.delete(`/tasks/sprints/${sprintId}`);
}

export async function addTaskToSprintApi(sprintId: string, taskId: string): Promise<SprintOut> {
  const r = await api.post<SprintOut>(`/tasks/sprints/${sprintId}/tasks`, { task_id: taskId });
  return r.data;
}

export async function removeTaskFromSprintApi(sprintId: string, taskId: string): Promise<SprintOut> {
  const r = await api.delete<SprintOut>(`/tasks/sprints/${sprintId}/tasks/${taskId}`);
  return r.data;
}

export async function getSprintTasksApi(sprintId: string): Promise<TaskListResponse> {
  const r = await api.get<TaskListResponse>(`/tasks/sprints/${sprintId}/tasks`);
  return r.data;
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export async function listPendingApprovalsApi(params?: {
  page?: number;
  size?: number;
}): Promise<ApprovalListResponse> {
  const r = await api.get<ApprovalListResponse>("/tasks/approvals/pending", { params });
  return r.data;
}

export async function requestApprovalApi(
  taskId: string,
  approverId: string
): Promise<ApprovalOut> {
  const r = await api.post<ApprovalOut>(`/tasks/${taskId}/approvals`, {
    approver_id: approverId,
  });
  return r.data;
}

export async function listTaskApprovalsApi(taskId: string): Promise<ApprovalOut[]> {
  const r = await api.get<ApprovalOut[]>(`/tasks/${taskId}/approvals`);
  return r.data;
}

export async function decideApprovalApi(
  approvalId: string,
  decision: "approved" | "rejected",
  note?: string
): Promise<ApprovalOut> {
  const r = await api.post<ApprovalOut>(`/tasks/approvals/${approvalId}/decide`, {
    decision,
    note,
  });
  return r.data;
}
