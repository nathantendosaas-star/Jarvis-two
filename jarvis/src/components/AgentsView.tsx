import React, { useState, useEffect } from "react";
import {
  Cpu,
  Database,
  Play,
  Pause,
  Sliders,
  Sparkles,
  RefreshCw,
  Activity,
  MoreVertical,
  Trash2,
  Zap,
  Clock
} from "lucide-react";
import { Agent } from "../types";

const AVAILABLE_TOOLS = [
  "read_file_content",
  "write_file_content",
  "execute_command",
  "execute_python_file",
  "grep_search",
  "web_fetch",
  "browser_automation",
  "save_memory"
];

interface AgentsViewProps {
  agents: Agent[];
  setAgents: React.Dispatch<React.SetStateAction<Agent[]>>;
  onUpdateAgent: (
    agentId: string,
    patch: {
      status?: string;
      priority?: string;
      cpu_allocation?: number;
      memory_allocation?: number;
      current_task?: string | null;
      activity?: string[];
    }
  ) => Promise<void>;
  onDeleteAgent: (agentId: string, deleteCache: boolean) => Promise<void>;
  onCreateAgent: (data: {
    name: string;
    role: string;
    avatar?: string;
    capabilities?: string[];
    tools?: string[];
  }) => Promise<void>;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function AgentsView({
  agents,
  setAgents,
  onUpdateAgent,
  onDeleteAgent,
  onCreateAgent,
  triggerNotification,
}: AgentsViewProps) {
  const [openMenuAgentId, setOpenMenuAgentId] = useState<string | null>(null);
  const [deletingAgent, setDeletingAgent] = useState<Agent | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newAvatar, setNewAvatar] = useState("🤖");
  const [newCapabilities, setNewCapabilities] = useState("");
  const [newTools, setNewTools] = useState<string[]>([]);

  useEffect(() => {
    const handleOutsideClick = () => setOpenMenuAgentId(null);
    window.addEventListener("click", handleOutsideClick);
    return () => window.removeEventListener("click", handleOutsideClick);
  }, []);

  const handleSetPriority = (id: string, priority: "high" | "medium" | "low") => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          triggerNotification("Priority Shift", `${a.name} task priority queue reallocated to ${priority.toUpperCase()}.`, "info");
          return {
            ...a,
            priority,
            activity: [`Task priority set to ${priority.toUpperCase()}`, ...a.activity]
          };
        }
        return a;
      })
    );
    onUpdateAgent(id, { priority });
  };
  
  const handleToggleStatus = (id: string) => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          const nextStatus = a.status === "working" || a.status === "idle" ? "paused" : "idle";
          triggerNotification("Agent Sync Update", `${a.name} status updated to: ${nextStatus}.`, "info");
          onUpdateAgent(id, {
            status: nextStatus,
            cpu_allocation: nextStatus === "paused" ? 0 : a.usage.cpu,
            memory_allocation: nextStatus === "paused" ? 0 : a.usage.memory,
          });
          return {
            ...a,
            status: nextStatus as any,
            usage: nextStatus === "paused" ? { cpu: 0, memory: 0 } : a.usage
          };
        }
        return a;
      })
    );
  };

  const handleRestartAgent = (id: string) => {
    const restartedCpu = 45;
    const restartedMem = 120;
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          triggerNotification("Orchestrator Action", `Rebooting ${a.name} cognitive node...`, "warning");
          return {
            ...a,
            status: "working" as any,
            usage: { cpu: restartedCpu, memory: restartedMem }
          };
        }
        return a;
      })
    );
    onUpdateAgent(id, { status: "working", cpu_allocation: restartedCpu, memory_allocation: restartedMem });
    setTimeout(() => {
      triggerNotification("Node Calibrated", `Agent successfully synchronized and online.`, "success");
    }, 1500);
  };

  const handleSliderChange = (id: string, field: "cpu" | "memory", value: number) => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          return {
            ...a,
            usage: {
              ...a.usage,
              [field]: value
            }
          };
        }
        return a;
      })
    );
    const patch = field === "cpu"
      ? { cpu_allocation: value }
      : { memory_allocation: value };
    onUpdateAgent(id, patch);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newRole.trim()) {
      triggerNotification("Input Required", "Please provide both Name and Role.", "warning");
      return;
    }
    const capabilitiesList = newCapabilities
      ? newCapabilities.split(",").map(c => c.trim()).filter(Boolean)
      : [];

    await onCreateAgent({
      name: newName,
      role: newRole,
      avatar: newAvatar,
      capabilities: capabilitiesList,
      tools: newTools
    });

    setNewName("");
    setNewRole("");
    setNewAvatar("🤖");
    setNewCapabilities("");
    setNewTools([]);
    setShowCreateModal(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
      
      {/* Intro Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
        <div>
          <h1 className="text-xl font-display font-bold text-white tracking-wide mt-0.5">Agent Workforce</h1>
          <p className="text-xs text-slate-400 mt-1">Deploy, monitor, and configure specialized AI agents in your environment.</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs font-mono text-slate-400">Active Agents: {agents.filter(a => a.status === 'working').length}</span>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer shadow"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Create Agent</span>
          </button>
        </div>
      </div>

      {/* Grid of Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.map((agent) => {
          const isWorking = agent.status === "working";
          const isPaused = agent.status === "paused";
          const isIdle = agent.status === "idle";

          return (
            <div
              key={agent.id}
              className={`glass-panel p-5 rounded-xl border transition-all relative ${
                isWorking
                  ? "border-blue-500/30 shadow-lg shadow-blue-500/5 bg-slate-900/50"
                  : "border-slate-800/60 bg-transparent"
              } flex flex-col justify-between space-y-4`}
            >
              {/* Header: Avatar, Name, Status Badge & Quick Actions Trigger */}
              <div className="flex items-start justify-between relative">
                <div className="flex gap-3">
                  <span className="text-3xl bg-slate-900 border border-slate-800 rounded-xl p-2.5 shadow-sm block leading-none shrink-0">
                    {agent.avatar}
                  </span>
                  <div>
                    <h3 className="font-bold text-white text-sm">{agent.name}</h3>
                    <span className="text-[10px] font-mono text-slate-500">{agent.role}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full font-bold uppercase ${
                      isWorking ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" :
                      isPaused ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                      "bg-slate-800/80 text-slate-400 border border-slate-700/50"
                    }`}>
                      {agent.status}
                    </span>
                    {agent.priority && (
                      <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider font-semibold ${
                        agent.priority === "high" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                        agent.priority === "medium" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" :
                        "bg-slate-800/50 text-slate-400 border-slate-700/30"
                      }`}>
                        {agent.priority}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenMenuAgentId(prev => prev === agent.id ? null : agent.id);
                    }}
                    className="p-1.5 bg-slate-900/60 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg text-slate-400 hover:text-white transition-all cursor-pointer"
                    title="Quick Actions"
                  >
                    <MoreVertical className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Floating Quick Actions Menu */}
              {openMenuAgentId === agent.id && (
                <div 
                  className="absolute right-5 top-16 w-52 bg-slate-950/95 backdrop-blur-lg border border-slate-800 rounded-xl shadow-2xl z-40 p-1.5 space-y-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="px-2.5 py-1 text-[9px] font-mono text-slate-500 uppercase tracking-widest font-semibold border-b border-slate-900/60 pb-1.5 mb-1">
                    Quick Actions
                  </div>

                  <button
                    onClick={() => {
                      handleToggleStatus(agent.id);
                      setOpenMenuAgentId(null);
                    }}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    {isWorking ? (
                      <>
                        <Pause className="w-3.5 h-3.5 text-amber-500" />
                        <span>Pause Operations</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Resume Operations</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => {
                      handleRestartAgent(agent.id);
                      setOpenMenuAgentId(null);
                    }}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                    <span>Restart / Reboot Node</span>
                  </button>

                  <button
                    onClick={() => {
                      setDeletingAgent(agent);
                      setOpenMenuAgentId(null);
                    }}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs hover:bg-red-950/40 text-red-400 hover:text-red-300 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    <span>Decommission Agent</span>
                  </button>
                </div>
              )}

              {/* LIVE NUMERICAL METRICS (Replaces heavy graph to eliminate page lag) */}
              <div className="grid grid-cols-3 gap-2 p-3 bg-slate-950/70 border border-slate-850 rounded-xl font-mono text-center">
                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-1 text-[9px] text-slate-500 uppercase">
                    <Cpu className="w-3 h-3 text-blue-400" />
                    <span>CPU</span>
                  </div>
                  <span className="text-sm font-bold text-white mt-1">{agent.usage.cpu}%</span>
                </div>

                <div className="flex flex-col items-center border-x border-slate-850">
                  <div className="flex items-center gap-1 text-[9px] text-slate-500 uppercase">
                    <Database className="w-3 h-3 text-purple-400" />
                    <span>RAM</span>
                  </div>
                  <span className="text-sm font-bold text-white mt-1">{agent.usage.memory}MB</span>
                </div>

                <div className="flex flex-col items-center">
                  <div className="flex items-center gap-1 text-[9px] text-slate-500 uppercase">
                    <Zap className="w-3 h-3 text-amber-400" />
                    <span>LATENCY</span>
                  </div>
                  <span className="text-sm font-bold text-emerald-400 mt-1">{isWorking ? "18ms" : "0ms"}</span>
                </div>
              </div>

              {/* Allocations Sliders */}
              <div className="space-y-3 pt-1">
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span>Allocated CPU Cycle Limit</span>
                    <span className="font-bold text-slate-300">{agent.usage.cpu}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    disabled={isPaused}
                    value={agent.usage.cpu}
                    onChange={(e) => handleSliderChange(agent.id, "cpu", parseInt(e.target.value))}
                    className="w-full accent-blue-500 h-1 bg-slate-900 rounded-lg cursor-pointer disabled:opacity-50"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span>Allocated RAM Storage Limit</span>
                    <span className="font-bold text-slate-300">{agent.usage.memory} MB</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="512"
                    step="8"
                    disabled={isPaused}
                    value={agent.usage.memory}
                    onChange={(e) => handleSliderChange(agent.id, "memory", parseInt(e.target.value))}
                    className="w-full accent-purple-500 h-1 bg-slate-900 rounded-lg cursor-pointer disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Capabilities */}
              <div className="space-y-1">
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Capabilities</span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.capabilities.map((cap, idx) => (
                    <span key={idx} className="text-[9px] font-mono bg-slate-950 border border-slate-850 px-2 py-0.5 rounded text-slate-400">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* Tools list */}
              <div className="space-y-1">
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Active Tools</span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.tools.map((tool, idx) => (
                    <span key={idx} className="text-[9px] font-mono bg-slate-900 border border-slate-800/60 px-2 py-0.5 rounded text-slate-400">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              {/* Status Task text */}
              {isWorking && agent.currentTask && (
                <div className="p-2.5 bg-slate-950/60 border border-slate-900 rounded-lg space-y-1">
                  <div className="flex items-center gap-1 text-[9px] font-mono text-slate-500 uppercase">
                    <Activity className="w-3 h-3 text-blue-400 animate-pulse" />
                    <span>Real-time Operation:</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-normal truncate">{agent.currentTask}</p>
                </div>
              )}

              {/* Action buttons footer */}
              <div className="flex gap-2 pt-2 border-t border-slate-800/40 justify-end">
                <button
                  onClick={() => handleToggleStatus(agent.id)}
                  className={`p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-all cursor-pointer ${
                    isWorking ? "text-amber-400" : "text-emerald-400"
                  }`}
                  title={isWorking ? "Pause Node Operations" : "Initiate Node Operations"}
                >
                  {isWorking ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => handleRestartAgent(agent.id)}
                  className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition-all cursor-pointer"
                  title="Calibrate / Reboot Node"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

            </div>
          );
        })}
      </div>

      {/* Decommission Agent Modal */}
      {deletingAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <Trash2 className="w-5 h-5" />
              <h3 className="text-sm font-bold text-white">Decommission {deletingAgent.name}?</h3>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Are you sure you want to decommission <strong>{deletingAgent.name}</strong>?
            </p>

            <div className="flex flex-col gap-2 pt-2">
              <button
                onClick={async () => {
                  const agentId = deletingAgent.id;
                  setDeletingAgent(null);
                  await onDeleteAgent(agentId, true);
                }}
                className="w-full py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Decommission Agent & Delete Cache
              </button>
              <button
                onClick={async () => {
                  const agentId = deletingAgent.id;
                  setDeletingAgent(null);
                  await onDeleteAgent(agentId, false);
                }}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-all cursor-pointer"
              >
                Decommission Agent Only (Keep Cache)
              </button>
              <button
                onClick={() => setDeletingAgent(null)}
                className="w-full py-2 border border-slate-800 hover:bg-slate-900 text-slate-400 rounded-lg text-xs font-medium transition-all cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Agent Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <form onSubmit={handleCreateSubmit} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center gap-3 text-blue-400">
              <Sparkles className="w-5 h-5" />
              <h3 className="text-sm font-bold text-white">Create New Agent</h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-1">Agent Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Lead Scraper"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-1">Role / Persona *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Market Research Specialist"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-1">Emoji Avatar</label>
                <input
                  type="text"
                  maxLength={2}
                  placeholder="🤖"
                  value={newAvatar}
                  onChange={(e) => setNewAvatar(e.target.value)}
                  className="w-12 text-center bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-1">Capabilities (comma separated)</label>
                <input
                  type="text"
                  placeholder="e.g. Scrape Web, Filter Leads"
                  value={newCapabilities}
                  onChange={(e) => setNewCapabilities(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase mb-1.5">Tool Access</label>
                <div className="grid grid-cols-2 gap-2 bg-slate-950 p-3 border border-slate-800 rounded-lg max-h-36 overflow-y-auto font-mono">
                  {AVAILABLE_TOOLS.map(t => (
                    <label key={t} className="flex items-center gap-2 text-[10px] text-slate-400 hover:text-white cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newTools.includes(t)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNewTools(prev => [...prev, t]);
                          } else {
                            setNewTools(prev => prev.filter(tool => tool !== t));
                          }
                        }}
                        className="accent-blue-500"
                      />
                      <span className="truncate">{t}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="flex-1 py-2 border border-slate-800 hover:bg-slate-900 text-slate-400 rounded-lg text-xs font-medium transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Save & Initialize
              </button>
            </div>
          </form>
        </div>
      )}

    </div>
  );
}
