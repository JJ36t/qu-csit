// API client helpers for admin panel
import { api } from "./client";

// ── Auth ──
export const authApi = {
  login: (university_id: string, password: string) =>
    api.post("/auth/login", { university_id, password }),
  me: () => api.get("/auth/me"),
  logout: (refresh_token?: string) =>
    api.post("/auth/logout", { refresh_token }),
};

// ── Academic structure ──
export const academicApi = {
  listDepartments: () => api.get("/admin/departments"),
  createDepartment: (data: unknown) => api.post("/admin/departments", data),
  listAcademicYears: () => api.get("/admin/academic-years"),
  createAcademicYear: (data: unknown) => api.post("/admin/academic-years", data),
  listTerms: (academicYearId?: string) =>
    api.get("/admin/terms", { params: { academic_year_id: academicYearId } }),
  createTerm: (data: unknown) => api.post("/admin/terms", data),
  generateSessions: (termId: string) =>
    api.post(`/admin/terms/${termId}/generate-sessions`),
  listGroups: (departmentId?: string, stage?: number) =>
    api.get("/admin/groups", { params: { department_id: departmentId, stage } }),
  createGroup: (data: unknown) => api.post("/admin/groups", data),
  listCourses: (departmentId?: string, stage?: number) =>
    api.get("/admin/courses", { params: { department_id: departmentId, stage } }),
  createCourse: (data: unknown) => api.post("/admin/courses", data),
  listOfferings: (termId?: string, groupId?: string, instructorId?: string) =>
    api.get("/admin/offerings", {
      params: { term_id: termId, group_id: groupId, instructor_id: instructorId },
    }),
  createOffering: (data: unknown) => api.post("/admin/offerings", data),
};

// ── Timetable ──
export const timetableApi = {
  getMy: (from: string, to: string) =>
    api.get("/timetable", { params: { from, to } }),
  getChanges: (from: string, to: string) =>
    api.get("/timetable/changes", { params: { from, to } }),
  createSlot: (data: unknown) => api.post("/admin/timetable", data),
  updateSlot: (slotId: string, data: unknown) =>
    api.patch(`/admin/timetable/${slotId}`, data),
  deleteSlot: (slotId: string) => api.delete(`/admin/timetable/${slotId}`),
  createChange: (data: unknown) => api.post("/admin/timetable/changes", data),
};

// ── Announcements ──
export const announcementsApi = {
  list: (page = 1, limit = 20) =>
    api.get("/announcements", { params: { page, limit } }),
  create: (data: unknown) => api.post("/announcements", data),
  markRead: (id: string) => api.post(`/announcements/${id}/read`),
  publicNews: (page = 1) => api.get("/public/news", { params: { page } }),
};

// ── Notifications ──
export const notificationsApi = {
  list: (unreadOnly = false, page = 1) =>
    api.get("/notifications", { params: { unread_only: unreadOnly, page } }),
  markAllRead: () => api.post("/notifications/read-all"),
  markOneRead: (id: string) => api.post(`/notifications/${id}/read`),
};

// ── Users ──
export const usersApi = {
  importStudents: (file: File, dryRun = true, initialPassword?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(
      `/admin/students/import?dry_run=${dryRun}${
        initialPassword ? `&initial_password=${initialPassword}` : ""
      }`,
      fd,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
  },
  commitStudentImport: (batchId: string) =>
    api.post(`/admin/students/import/${batchId}/commit`),
  resetPassword: (userId: string, newPassword?: string) =>
    api.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword }),
  toggleStatus: (userId: string) =>
    api.post(`/admin/users/${userId}/toggle-status`),
  unbindDevice: (userId: string) =>
    api.post("/admin/users/unbind-device", { user_id: userId }),
};

// ── Term absence rules ──
export const absenceRulesApi = {
  list: (termId?: string) =>
    api.get("/admin/term-absence-rules", { params: { term_id: termId } }),
  upsert: (data: unknown) => api.post("/admin/term-absence-rules", data),
};

// ── Audit logs ──
export const auditApi = {
  list: (params?: { entity?: string; actor_id?: string; page?: number; limit?: number }) =>
    api.get("/admin/audit-logs", { params }),
};
