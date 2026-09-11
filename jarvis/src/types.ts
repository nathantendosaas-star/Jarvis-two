export type WorkspaceView =
  | "dashboard"
  | "chat"
  | "projects"
  | "agents"
  | "files"
  | "browser"
  | "memory"
  | "automation"
  | "settings";

export interface Project {
  id: string;
  name: string;
  description: string;
  status: "active" | "completed" | "paused";
  tags: string[];
  client?: string;
  tasksCount: number;
  completedTasksCount: number;
  lastUpdated: string;
  color: string;
  createdAt?: string;
  updatedAt?: string;
  fileCount?: number;
  storageBytes?: number;
  notes?: string;
  activity?: { time: string; text: string }[];
}

export interface BackendProject {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  avatar: string;
  status: "idle" | "working" | "offline" | "paused";
  currentTask?: string;
  priority?: "high" | "medium" | "low";
  usage: {
    cpu: number;
    memory: number; // in MB
  };
  performance: number; // success rate %
  tools: string[];
  memoryCount: number;
  capabilities: string[];
  activity: string[];
}

export interface FileNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileNode[];
  content?: string;
  type?: "directory" | "code" | "image" | "pdf" | "markdown" | "text" | "audio" | "video";
  size?: number;
  modifiedAt?: string;
  projectId?: string;
  id?: string;
}

export interface BackendFile {
  id: string;
  project_id: string;
  filename: string;
  path: string;
  size?: number;
  mime_type?: string;
  created_at: string;
}

export interface BrowserTab {
  id: string;
  title: string;
  url: string;
  status: "loaded" | "loading" | "error";
  content: string;
  screenshot?: string;
  consoleLogs?: string[];
}

export interface MemoryItem {
  id: string;
  text: string;
  type: "user_preference" | "project_fact" | "writing_style" | "relationship";
  timestamp: string;
  importance: number; // 1 to 5 stars
}

export interface WorkflowNode {
  id: string;
  name: string;
  type: "trigger" | "condition" | "ai" | "action" | "notification";
  status: "active" | "pending" | "running" | "completed" | "failed";
  config: Record<string, any>;
}

export interface Task {
  id: string;
  project_id: string;
  chat_id?: string | null;
  title: string;
  description?: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | string;
  logs?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface WorkflowConnection {
  from: string;
  to: string;
}

export interface SystemMetrics {
  cpu: number;
  ram: number; // GB
  networkSpeed: number; // MB/s
  storage: number; // GB used
  apiCalls: number;
  activeAgents: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "model";
  content: string;
  timestamp: string;
  model?: string;
  useSearch?: boolean;
  webCitations?: { uri: string; title: string }[];
  isThinking?: boolean;
  toolCall?: {
    name: string;
    args: Record<string, any>;
    status: "running" | "completed" | "failed";
  };
}

export interface SystemNotification {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error" | "agent";
  time: string;
  read: boolean;
}
