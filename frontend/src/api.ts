import type { Room, Student, Subject, Teacher, Course, CourseForm, Attendance, AttendanceReport, ScheduleAdjustment } from "./types";

const BASE = import.meta.env.DEV ? "/api" : "";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(BASE + url, { headers, ...options });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") || "";
  try {
    return await res.json();
  } catch {
    throw new Error(contentType.includes("text/html")
      ? "服务器返回了网页而非JSON数据，请确认连接的是正确的服务端口"
      : "服务器返回了意外的响应，请检查服务是否正常运行");
  }
}

export const api = {
  rooms: {
    list: () => request<Room[]>("/rooms/"),
    get: (id: number) => request<Room>(`/rooms/${id}`),
    create: (data: Omit<Room, "id">) => request<Room>("/rooms/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Omit<Room, "id">) => request<Room>(`/rooms/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/rooms/${id}`, { method: "DELETE" }),
  },
  students: {
    list: () => request<Student[]>("/students/"),
    get: (id: number) => request<Student>(`/students/${id}`),
    create: (data: Omit<Student, "id">) => request<Student>("/students/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Omit<Student, "id">) => request<Student>(`/students/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/students/${id}`, { method: "DELETE" }),
  },
  subjects: {
    list: () => request<Subject[]>("/subjects/"),
    create: (data: { name: string }) => request<Subject>("/subjects/", { method: "POST", body: JSON.stringify(data) }),
  },
  teachers: {
    list: () => request<Teacher[]>("/teachers/"),
    get: (id: number) => request<Teacher>(`/teachers/${id}`),
    create: (data: { name: string; phone: string; notes: string; subject_ids: number[] }) =>
      request<Teacher>("/teachers/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: { name: string; phone: string; notes: string; subject_ids: number[] }) =>
      request<Teacher>(`/teachers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/teachers/${id}`, { method: "DELETE" }),
  },
  courses: {
    list: (dayOfWeek?: number) =>
      request<Course[]>(`/courses/${dayOfWeek !== undefined ? `?day_of_week=${dayOfWeek}` : ""}`),
    get: (id: number) => request<Course>(`/courses/${id}`),
    create: (data: CourseForm) => request<Course>("/courses/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<CourseForm>) =>
      request<Course>(`/courses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/courses/${id}`, { method: "DELETE" }),
  },
  auth: {
    login: (username: string, password: string) =>
      request<{ token: string; username: string; role: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
    register: (username: string, password: string) =>
      request<{ ok: boolean }>("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
    logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }).finally(() => localStorage.removeItem("auth_token")),
    me: () => request<{ username: string; role: string }>("/auth/me"),
  },
  attendance: {
    list: (courseId?: number, dateVal?: string) => {
      const params = new URLSearchParams(); if (courseId) params.set("course_id", String(courseId));
      if (dateVal) params.set("date_val", dateVal); return request<Attendance[]>(`/attendance/?${params}`);
    },
    batch: (data: { course_id: number; date_val: string; records: { student_id: number; status: string; notes: string }[] }) =>
      request<{ ok: boolean }>("/attendance/batch", { method: "POST", body: JSON.stringify(data) }),
    report: (studentId?: number, dateFrom?: string, dateTo?: string) => {
      const params = new URLSearchParams(); if (studentId) params.set("student_id", String(studentId));
      if (dateFrom) params.set("date_from", dateFrom); if (dateTo) params.set("date_to", dateTo);
      return request<AttendanceReport[]>(`/attendance/report?${params}`);
    },
  },
  adjustments: {
    list: (courseId?: number, dateVal?: string) => {
      const params = new URLSearchParams(); if (courseId) params.set("course_id", String(courseId));
      if (dateVal) params.set("date_val", dateVal); return request<ScheduleAdjustment[]>(`/adjustments/?${params}`);
    },
    create: (data: { course_id: number; adjustment_date: string; original_day: number; original_slot: number;
      original_room_id: number; new_day?: number; new_slot?: number; new_room_id?: number; adjustment_type: string; reason: string }) =>
      request<ScheduleAdjustment>("/adjustments/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: any) => request<ScheduleAdjustment>(`/adjustments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<void>(`/adjustments/${id}`, { method: "DELETE" }),
  },
};
