import { Agent, BackendFile, BackendProject, FileNode, Project, Task } from "./types";

const TOKEN_KEY = "jarvisAccessToken";
const PASSWORD_KEY = "jarvisPassword";
const DEFAULT_LOCAL_PASSWORD = "jarvis";

type RequestOptions = RequestInit & { retry?: boolean };

async function login() {
  const password = localStorage.getItem(PASSWORD_KEY) || DEFAULT_LOCAL_PASSWORD;
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    throw new Error("Authentication failed. Set the UI password in localStorage under jarvisPassword.");
  }

  const data = await response.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data.access_token as string;
}

async function authToken() {
  return localStorage.getItem(TOKEN_KEY) || login();
}

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = await authToken();
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && options.retry !== false) {
    localStorage.removeItem(TOKEN_KEY);
    await login();
    return apiRequest<T>(path, { ...options, retry: false });
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

function formatDate(value?: string) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function projectStatus(tasks: Task[]): Project["status"] {
  if (tasks.length === 0) return "active";
  if (tasks.every(task => task.status === "completed" || task.status === "cancelled")) return "completed";
  if (tasks.some(task => task.status === "running" || task.status === "queued")) return "active";
  return "paused";
}

function mapBackendProject(project: BackendProject, tasks: Task[], files: BackendFile[]): Project {
  const completedTasks = tasks.filter(task => task.status === "completed").length;
  const storageBytes = files.reduce((total, file) => total + (file.size || 0), 0);

  return {
    id: project.id,
    name: project.name,
    description: project.description || "No description provided.",
    status: projectStatus(tasks),
    tags: [],
    tasksCount: tasks.length,
    completedTasksCount: completedTasks,
    lastUpdated: formatDate(project.updated_at),
    createdAt: project.created_at,
    updatedAt: project.updated_at,
    color: project.color || "#3b82f6",
    fileCount: files.length,
    storageBytes,
    notes: "",
    activity: tasks
      .slice()
      .sort((a, b) => String(b.started_at || b.finished_at || "").localeCompare(String(a.started_at || a.finished_at || "")))
      .slice(0, 8)
      .map(task => ({
        time: formatDate(task.finished_at || task.started_at || project.updated_at),
        text: `${task.status.toUpperCase()}: ${task.title}`,
      })),
  };
}

export async function fetchWorkspaceData() {
  const projects = await apiRequest<BackendProject[]>("/api/projects/");
  const details = await Promise.all(
    projects.map(async project => {
      const [tasks, files] = await Promise.all([
        apiRequest<Task[]>(`/api/tasks/${project.id}`),
        apiRequest<BackendFile[]>(`/api/files/${project.id}`),
      ]);
      return { project, tasks, files };
    }),
  );

  const tasksByProject: Record<string, Task[]> = {};
  const filesByProject: Record<string, BackendFile[]> = {};

  const mappedProjects = details.map(({ project, tasks, files }) => {
    tasksByProject[project.id] = tasks;
    filesByProject[project.id] = files;
    return mapBackendProject(project, tasks, files);
  });

  return { projects: mappedProjects, tasksByProject, filesByProject };
}

export async function createProject(data: { name: string; description?: string; color?: string }) {
  const project = await apiRequest<BackendProject>("/api/projects/", {
    method: "POST",
    body: JSON.stringify(data),
  });

  return mapBackendProject(project, [], []);
}

export async function updateProject(projectId: string, data: { description?: string; name?: string; color?: string }) {
  const project = await apiRequest<BackendProject>(`/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

  return project;
}

export async function fetchWorkspaceFiles() {
  return apiRequest<FileNode[]>("/api/files/workspace/tree");
}

// ---------------------------------------------------------------------------
// Agent API
// ---------------------------------------------------------------------------

interface BackendAgent {
  id: string;
  name: string;
  role: string;
  avatar: string;
  status: "idle" | "working" | "paused" | "offline";
  current_task?: string | null;
  priority: "high" | "medium" | "low";
  cpu_allocation: number;
  memory_allocation: number;
  capabilities: string[];
  tools: string[];
  activity: string[];
  performance: number;
  created_at: string;
  updated_at: string;
}

function mapBackendAgent(a: BackendAgent): Agent {
  return {
    id: a.id,
    name: a.name,
    role: a.role,
    avatar: a.avatar,
    status: a.status,
    currentTask: a.current_task ?? undefined,
    priority: a.priority,
    usage: {
      cpu: a.cpu_allocation,
      memory: a.memory_allocation,
    },
    performance: a.performance,
    tools: a.tools,
    memoryCount: 0,
    capabilities: a.capabilities,
    activity: a.activity,
  };
}

export async function fetchAgents(): Promise<Agent[]> {
  const agents = await apiRequest<BackendAgent[]>("/api/agents/");
  return agents.map(mapBackendAgent);
}

export async function createAgent(data: {
  name: string;
  role: string;
  avatar?: string;
  capabilities?: string[];
  tools?: string[];
}): Promise<Agent> {
  const agent = await apiRequest<BackendAgent>("/api/agents/", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return mapBackendAgent(agent);
}

export async function updateAgent(
  agentId: string,
  data: {
    status?: string;
    priority?: string;
    cpu_allocation?: number;
    memory_allocation?: number;
    current_task?: string | null;
    activity?: string[];
  }
): Promise<Agent> {
  const agent = await apiRequest<BackendAgent>(`/api/agents/${agentId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  return mapBackendAgent(agent);
}

export async function deleteAgent(agentId: string, deleteCache: boolean = false): Promise<void> {
  return apiRequest<void>(`/api/agents/${agentId}?delete_cache=${deleteCache}`, { method: "DELETE" });
}
