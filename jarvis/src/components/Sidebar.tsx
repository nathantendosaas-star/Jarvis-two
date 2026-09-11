import React from "react";
import {
  LayoutDashboard,
  MessageSquare,
  FolderKanban,
  Bot,
  FolderOpen,
  Globe,
  BrainCircuit,
  Zap,
  Settings,
  Terminal,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Command
} from "lucide-react";
import { WorkspaceView, Project } from "../types";

interface SidebarProps {
  currentView: WorkspaceView;
  setCurrentView: (view: WorkspaceView) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  projects: Project[];
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
  toggleCommandPalette: () => void;
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (isOpen: boolean) => void;
}

export default function Sidebar({
  currentView,
  setCurrentView,
  collapsed,
  setCollapsed,
  projects,
  activeProjectId,
  setActiveProjectId,
  toggleCommandPalette,
  isMobileMenuOpen,
  setIsMobileMenuOpen,
}: SidebarProps) {
  const mainNavItems = [
    { view: "dashboard" as WorkspaceView, label: "Dashboard", icon: LayoutDashboard, color: "text-blue-400" },
    { view: "chat" as WorkspaceView, label: "AI Chat", icon: MessageSquare, color: "text-purple-400" },
    { view: "projects" as WorkspaceView, label: "Workspaces", icon: FolderKanban, color: "text-indigo-400" },
    { view: "agents" as WorkspaceView, label: "Agents", icon: Bot, color: "text-emerald-400" },
    { view: "files" as WorkspaceView, label: "Files", icon: FolderOpen, color: "text-amber-400" },
    { view: "browser" as WorkspaceView, label: "Browser", icon: Globe, color: "text-cyan-400" },
    { view: "memory" as WorkspaceView, label: "Memory", icon: BrainCircuit, color: "text-pink-400" },
    { view: "automation" as WorkspaceView, label: "Automations", icon: Zap, color: "text-orange-400" },
  ];

  const utilityNavItems = [
    { view: "settings" as WorkspaceView, label: "Settings", icon: Settings, color: "text-slate-400" },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      <aside
        id="jarvis-sidebar"
        className={`h-screen flex flex-col glass-panel border-r border-slate-800/60 text-slate-200 transition-all duration-300 z-50 fixed md:relative ${
          collapsed ? "w-20" : "w-64"
        } ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
      {/* Brand Header */}
      <div className="p-5 flex items-center justify-between border-b border-slate-800/40">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="p-2 bg-slate-800 rounded-lg flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div className="flex flex-col select-none">
              <span className="font-display font-semibold tracking-wide text-white text-lg">JARVIS</span>
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest font-semibold">WORKSPACE</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 hover:bg-slate-800/60 rounded-md text-slate-400 hover:text-white transition-colors duration-150 cursor-pointer md:block hidden"
          id="toggle-sidebar"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Quick Search trigger button in sidebar */}
      {!collapsed && (
        <div className="px-4 py-3">
          <button
            onClick={toggleCommandPalette}
            className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/50 hover:bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 rounded-lg text-xs text-slate-400 transition-all group cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Command className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400" />
              <span>Command Palette</span>
            </div>
            <kbd className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-800 border border-slate-700/60 rounded text-slate-500">⌘K</kbd>
          </button>
        </div>
      )}

      {/* Main Navigation Items */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.view;
          return (
            <button
              key={item.view}
              id={`nav-${item.view}`}
              onClick={() => {
                setCurrentView(item.view);
                setActiveProjectId(null); // Clear selected project when going to main views
              }}
              className={`w-full flex items-center gap-3.5 px-3.5 py-3 rounded-lg text-sm transition-all duration-150 group cursor-pointer ${
                isActive
                  ? "bg-blue-600/10 text-blue-400 border-l-2 border-blue-500 font-medium"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40"
              }`}
            >
              <Icon className={`w-5 h-5 shrink-0 ${isActive ? item.color : "text-slate-400 group-hover:" + item.color} transition-colors`} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </button>
          );
        })}

        {/* Separator */}
        {!collapsed && (
          <div className="pt-4 pb-2 px-3">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Active Workspace</span>
          </div>
        )}

        {/* Projects / Workspaces List */}
        {!collapsed ? (
          <div className="space-y-1">
            {projects.slice(0, 3).map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  setCurrentView("projects");
                  setActiveProjectId(project.id);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs transition-all cursor-pointer ${
                  activeProjectId === project.id
                    ? "bg-purple-600/15 text-purple-300 font-medium border-l-2 border-purple-500"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
                    style={{ backgroundColor: project.color }}
                  />
                  <span className="truncate">{project.name}</span>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800/50">
                  {project.completedTasksCount}/{project.tasksCount}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="h-0.5 bg-slate-800/40 my-4" />
        )}
      </div>

      {/* Utility / Footer Section */}
      <div className="p-3 border-t border-slate-800/40 space-y-1">
        {utilityNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.view;
          return (
            <button
              key={item.view}
              id={`nav-${item.view}`}
              onClick={() => {
                setCurrentView(item.view);
                setActiveProjectId(null);
              }}
              className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-lg text-sm transition-all duration-150 cursor-pointer ${
                isActive
                  ? "bg-slate-800 text-white font-medium"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
              }`}
            >
              <Icon className="w-5 h-5 shrink-0 text-slate-400 group-hover:text-white" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}

      </div>
    </aside>
    </>
  );
}
