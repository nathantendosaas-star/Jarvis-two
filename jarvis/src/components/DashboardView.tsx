import React from "react";
import {
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { Project, Agent, SystemMetrics, SystemNotification } from "../types";

interface DashboardViewProps {
  projects: Project[];
  agents: Agent[];
  metrics: SystemMetrics;
  notifications: SystemNotification[];
  setActiveView: (view: any) => void;
  setActiveProjectId: (id: string | null) => void;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function DashboardView({
  projects,
  agents,
  metrics,
  setActiveView,
  setActiveProjectId,
}: DashboardViewProps) {
  const activeWorkspaces = projects.filter(p => p.status === "active");
  const completedTasks = projects.reduce((total, project) => total + project.completedTasksCount, 0);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
      
      {/* Welcome banner with simple, modern typography */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/10 border border-slate-800/40 p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-display font-semibold text-white tracking-wide">
            Workspace Overview
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-xl leading-relaxed">
            Showing {projects.length} backend workspace{projects.length === 1 ? "" : "s"} and {metrics.networkSpeed} uploaded file record{metrics.networkSpeed === 1 ? "" : "s"}.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveView("chat")}
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-lg text-xs transition-all flex items-center gap-1.5 cursor-pointer border border-slate-700/50"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>AI Chat</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          </button>
        </div>
      </div>

      {/* Understated Stat Row */}
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 text-xs text-slate-400 bg-slate-900/30 border border-slate-800/40 rounded-xl px-5 py-3 font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Workspaces:</span>
          <span className="text-blue-400 font-bold">{metrics.cpu}</span>
        </div>
        <div className="hidden sm:block text-slate-800">|</div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Uploaded Storage:</span>
          <span className="text-purple-400 font-bold">{metrics.ram} MB</span>
        </div>
        <div className="hidden sm:block text-slate-800">|</div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Tasks:</span>
          <span className="text-emerald-400 font-bold">{completedTasks} / {metrics.storage}</span>
        </div>
        <div className="hidden sm:block text-slate-800">|</div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500">Active Workspaces:</span>
          <span className="text-amber-400 font-bold">{activeWorkspaces.length}</span>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Real workspace list */}
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-display font-semibold text-white tracking-wide">Workspaces</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Projects loaded from the local database</p>
              </div>
              <span className="text-xs text-slate-400 font-semibold font-mono">
                {activeWorkspaces.length} active
              </span>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {projects.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                  No workspaces exist in the database yet. Create one from the Workspaces screen.
                </div>
              ) : (
                projects.map(project => {
                  const pct = Math.round((project.completedTasksCount / Math.max(project.tasksCount, 1)) * 100);
                  return (
                    <button
                      key={project.id}
                      onClick={() => {
                        setActiveProjectId(project.id);
                        setActiveView("projects");
                      }}
                      className="w-full p-3 rounded-lg border bg-slate-950/20 hover:bg-slate-900/40 border-slate-800/40 hover:border-slate-700/50 text-slate-200 transition-all cursor-pointer text-left"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                          <div className="min-w-0">
                            <span className="text-xs font-medium truncate block">{project.name}</span>
                            <span className="text-[10px] text-slate-500 font-mono">{project.fileCount || 0} files · {project.tasksCount} tasks · updated {project.lastUpdated}</span>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-slate-400">{pct}%</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Active Workforce (Takes 1 column on desktop) */}
        <div className="space-y-4">
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-display font-semibold text-white tracking-wide">Active Workforce</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">Agent data source is not connected yet</p>
              </div>
              <button
                onClick={() => setActiveView("agents")}
                className="text-xs text-blue-400 hover:text-blue-300 font-semibold cursor-pointer"
              >
                View All
              </button>
            </div>

            <div className="space-y-3">
              {agents.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
                  No backend agent records available.
                </div>
              ) : (
                agents.slice(0, 4).map(agent => (
                  <div key={agent.id} className="p-3 bg-slate-900/20 rounded-lg border border-slate-800/40">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="text-lg">{agent.avatar}</span>
                        <div>
                          <h4 className="text-xs font-bold text-white">{agent.name}</h4>
                          <span className="text-[10px] text-slate-500 font-mono">{agent.role}</span>
                        </div>
                      </div>
                      <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full font-semibold uppercase ${
                        agent.status === 'working' ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "bg-slate-800 text-slate-500 border border-slate-700/30"
                      }`}>
                        {agent.status}
                      </span>
                    </div>

                    {agent.status === "working" && agent.currentTask && (
                      <div className="pt-2 mt-2 border-t border-slate-800/40 text-[11px]">
                        <p className="text-slate-400 font-mono text-[9px] uppercase tracking-wider mb-0.5">Active Operation:</p>
                        <p className="text-slate-300 font-medium truncate">{agent.currentTask}</p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
