import React, { useState } from "react";
import {
  Folder,
  Plus,
  FileText,
  CircleDot,
  Share2,
  ArrowLeft
} from "lucide-react";
import { Project } from "../types";
import { createProject, updateProject } from "../api";

interface ProjectsViewProps {
  projects: Project[];
  setProjects: React.Dispatch<React.SetStateAction<Project[]>>;
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function ProjectsView({
  projects,
  setProjects,
  activeProjectId,
  setActiveProjectId,
  triggerNotification,
}: ProjectsViewProps) {
  const [showAddProject, setShowAddProject] = useState(false);
  const [newProjName, setNewProjName] = useState("");
  const [newProjDesc, setNewProjDesc] = useState("");
  const [newProjColor, setNewProjColor] = useState("#3b82f6");
  const [isSaving, setIsSaving] = useState(false);

  // Scratchpad edit mode
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [notesText, setNotesText] = useState("");

  const activeProject = projects.find(p => p.id === activeProjectId) || null;

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim()) return;
    setIsSaving(true);

    try {
      const newProject = await createProject({
        name: newProjName,
        description: newProjDesc,
        color: newProjColor,
      });
      setProjects([newProject, ...projects]);
      setActiveProjectId(newProject.id);
      setShowAddProject(false);
      setNewProjName("");
      setNewProjDesc("");
      triggerNotification("Workspace Created", `Saved "${newProject.name}" to the local database.`, "success");
    } catch (error) {
      triggerNotification("Workspace Create Failed", error instanceof Error ? error.message : "Unable to create workspace.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateNotes = async () => {
    if (!activeProject) return;
    setIsSaving(true);
    try {
      await updateProject(activeProject.id, { description: notesText });
      setProjects(prev =>
        prev.map(p => (p.id === activeProject.id ? { ...p, description: notesText, notes: notesText } : p))
      );
      setIsEditingNotes(false);
      triggerNotification("Workspace Updated", "Description saved to the local database.", "success");
    } catch (error) {
      triggerNotification("Workspace Update Failed", error instanceof Error ? error.message : "Unable to update workspace.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const startEditingNotes = () => {
    if (!activeProject) return;
    setNotesText(activeProject.notes || activeProject.description || "");
    setIsEditingNotes(true);
  };

  return (
    <div className="flex-1 flex overflow-hidden text-slate-200 relative h-full">
      
      {/* Left panel: workspaces tree or list */}
      <div className={`${activeProject ? 'hidden md:flex' : 'flex'} w-full md:w-80 border-r border-slate-800/40 p-5 flex-col h-full bg-slate-950/10 overflow-y-auto shrink-0 z-10 md:static absolute inset-0 bg-jarvis-bg`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider">Active Workspaces</h2>
          <button
            onClick={() => setShowAddProject(!showAddProject)}
            className="p-1.5 hover:bg-slate-800 rounded-lg text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
            title="Create Workspace"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Create workspace form */}
        {showAddProject && (
          <form onSubmit={handleCreateProject} className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl mb-4 space-y-3 animate-fade-in text-xs">
            <div>
              <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Project Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Kampala Outreach"
                value={newProjName}
                onChange={(e) => setNewProjName(e.target.value)}
                className="w-full glass-input px-2.5 py-1.5 text-xs"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Description</label>
              <textarea
                placeholder="Brief purpose..."
                value={newProjDesc}
                onChange={(e) => setNewProjDesc(e.target.value)}
                className="w-full glass-input px-2.5 py-1.5 text-xs h-16 resize-none"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Accent Color</label>
              <div className="flex items-center gap-2">
                {["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"].map(c => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setNewProjColor(c)}
                    className={`w-5 h-5 rounded-full border border-slate-950 transition-transform ${
                      newProjColor === c ? "scale-125 ring-1 ring-white/50" : "hover:scale-110"
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <button
              type="submit"
              disabled={isSaving}
              className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg font-bold text-white transition-all cursor-pointer"
            >
              {isSaving ? "Saving..." : "Create Workspace"}
            </button>
          </form>
        )}

        {/* Project Workspaces Cards */}
        <div className="space-y-2">
          {projects.length === 0 && (
            <div className="p-6 border border-dashed border-slate-800 rounded-xl text-center text-xs text-slate-500">
              No workspaces found in the local database.
            </div>
          )}
          {projects.map(p => {
            const pct = Math.round((p.completedTasksCount / Math.max(p.tasksCount, 1)) * 100) || 0;
            const isSelected = activeProjectId === p.id;
            return (
              <div
                key={p.id}
                onClick={() => setActiveProjectId(p.id)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer text-xs ${
                  isSelected
                    ? "bg-slate-900 border-slate-700 shadow-md"
                    : "bg-transparent border-slate-850 hover:bg-slate-900/30 hover:border-slate-800"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse" style={{ backgroundColor: p.color }} />
                    <h3 className={`font-bold truncate ${isSelected ? "text-white" : "text-slate-300"}`}>{p.name}</h3>
                  </div>
                  <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
                    p.status === 'active' ? "text-blue-400 bg-blue-400/5" : "text-slate-400 bg-slate-400/5"
                  }`}>
                    {p.status}
                  </span>
                </div>

                <p className="text-slate-400 text-[11px] mt-1 line-clamp-2 leading-relaxed">{p.description}</p>

                {/* Tags */}
                {p.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2.5">
                  {p.tags.map((t, idx) => (
                    <span key={idx} className="text-[9px] font-mono bg-slate-900 border border-slate-800/80 px-1.5 py-0.2 rounded text-slate-500">
                      {t}
                    </span>
                  ))}
                </div>
                )}

                {/* Progress bar */}
                <div className="mt-3.5 space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span>{p.completedTasksCount}/{p.tasksCount} tasks · {p.fileCount || 0} files</span>
                    <span className="font-bold text-slate-400">{p.tasksCount ? `${pct}%` : "No tasks"}</span>
                  </div>
                  <div className="w-full bg-slate-950 h-1 rounded-full overflow-hidden">
                    <div className="bg-blue-500 h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: p.color }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right panel: Workspace Active View details */}
      <div className={`${!activeProject ? 'hidden md:block' : 'block'} flex-1 overflow-y-auto p-6 space-y-6`}>
        {activeProject ? (
          <div className="space-y-6 animate-fade-in">
            
            {/* Header Area */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
              <div>
                <button
                  onClick={() => setActiveProjectId(null)}
                  className="md:hidden flex items-center gap-1 text-slate-400 hover:text-white mb-2 text-xs"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Workspaces</span>
                </button>
                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                  <span>WORKSPACE_ID: {activeProject.id}</span>
                  <span>•</span>
                  <span>Updated: {activeProject.lastUpdated}</span>
                </div>
                <h1 className="text-xl font-display font-bold text-white tracking-wide mt-1">{activeProject.name}</h1>
                <p className="text-xs text-slate-400 mt-1">{activeProject.description}</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => triggerNotification("Workspace Shared", "Generated shareable workspace token.", "success")}
                  className="p-2 bg-slate-900/50 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
                  title="Share workspace link"
                >
                  <Share2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Middle Workspace: Notes and logs split */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Scratchpad */}
              <div className="glass-panel p-5 rounded-xl border border-slate-800/60 flex flex-col h-96">
                <div className="flex items-center justify-between mb-3 shrink-0">
                  <div className="flex items-center gap-2 text-xs font-mono">
                    <FileText className="w-4 h-4 text-purple-400" />
                    <span className="font-bold uppercase text-slate-400">Workspace Description</span>
                  </div>
                  {isEditingNotes ? (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setIsEditingNotes(false)}
                        className="text-[10px] text-slate-500 hover:text-slate-400 font-bold"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleUpdateNotes}
                        disabled={isSaving}
                        className="text-[10px] text-blue-400 hover:text-blue-300 font-bold"
                      >
                        {isSaving ? "Saving..." : "Save"}
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={startEditingNotes}
                      className="text-[10px] text-blue-400 hover:text-blue-300 font-semibold cursor-pointer"
                    >
                      Edit Markdown
                    </button>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto">
                  {isEditingNotes ? (
                    <textarea
                      value={notesText}
                      onChange={(e) => setNotesText(e.target.value)}
                      className="w-full h-full bg-slate-950/60 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 resize-none focus:outline-none focus:border-blue-500"
                    />
                  ) : (
                    <div className="text-xs text-slate-300 space-y-2 font-sans leading-relaxed whitespace-pre-wrap">
                      {activeProject.notes || activeProject.description || "No description saved for this workspace yet."}
                    </div>
                  )}
                </div>
              </div>

              {/* Activity log timeline */}
              <div className="glass-panel p-5 rounded-xl border border-slate-800/60 flex flex-col h-96">
                <div className="flex items-center justify-between mb-3 shrink-0">
                  <div className="flex items-center gap-2 text-xs font-mono">
                    <CircleDot className="w-4 h-4 text-blue-400" />
                    <span className="font-bold uppercase text-slate-400">Workspace Activity Feed</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Task events</span>
                </div>

                <div className="flex-1 overflow-y-auto pr-1 space-y-3">
                  {activeProject.activity && activeProject.activity.length > 0 ? (
                    activeProject.activity.map((act, idx) => (
                      <div key={idx} className="flex gap-2.5 text-xs animate-fade-in border-l border-slate-800 pl-3 relative">
                        <div className="absolute top-1.5 -left-1 w-2 h-2 rounded-full bg-blue-500" />
                        <div className="flex-1">
                          <span className="text-[10px] font-mono text-slate-500 block">{act.time}</span>
                          <p className="text-slate-300 mt-0.5 font-medium leading-relaxed">{act.text}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-slate-500 py-10 text-xs">No task activity recorded for this workspace.</div>
                  )}
                </div>
              </div>

            </div>

          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-12 text-slate-500">
            <Folder className="w-12 h-12 text-slate-700 mb-3" />
            <h3 className="text-sm font-bold text-white">No active workspace expanded</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">Select one of your environments on the left side menu to monitor task queues, write notes, and analyze telemetry.</p>
          </div>
        )}
      </div>

    </div>
  );
}
