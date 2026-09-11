import React, { useState } from "react";
import {
  Brain,
  Search,
  Plus,
  Trash2,
  Star,
  CheckCircle2,
  Award,
  BookOpen,
  UserCheck,
  Globe,
  PlusCircle
} from "lucide-react";
import { MemoryItem, Agent, Project } from "../types";
import NeuralNetworkGraph from "./NeuralNetworkGraph";

interface MemoryViewProps {
  memories: MemoryItem[];
  setMemories: React.Dispatch<React.SetStateAction<MemoryItem[]>>;
  agents: Agent[];
  projects: Project[];
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function MemoryView({
  memories,
  setMemories,
  agents,
  projects,
  triggerNotification,
}: MemoryViewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [newMemoryText, setNewMemoryText] = useState("");
  const [newMemoryType, setNewMemoryType] = useState<any>("user_preference");
  const [newMemoryStars, setNewMemoryStars] = useState(3);
  const [activeTab, setActiveTab] = useState<"ledger" | "graph">("graph");

  const handleAddMemory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryText.trim()) return;

    const newItem: MemoryItem = {
      id: "mem-" + Date.now(),
      text: newMemoryText,
      type: newMemoryType,
      timestamp: new Date().toLocaleDateString(),
      importance: newMemoryStars
    };

    setMemories([newItem, ...memories]);
    setNewMemoryText("");
    triggerNotification("Synaptic Index Written", "Memory rule successfully written to core neural storage.", "success");
  };

  const handleDeleteMemory = (id: string) => {
    setMemories(prev => prev.filter(m => m.id !== id));
    triggerNotification("Synapse Cleared", "Neural connection severed.", "info");
  };

  const handleAdjustStars = (id: string, stars: number) => {
    setMemories(prev =>
      prev.map(m => (m.id === id ? { ...m, importance: stars } : m))
    );
    triggerNotification("Neuron Calibrated", "Adjusted semantic importance weighting.", "success");
  };

  const filteredMemories = memories.filter(
    m =>
      m.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200 flex flex-col h-full">
      
      {/* Intro header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
        <div>
          <h1 className="text-xl font-display font-bold text-white tracking-wide mt-0.5">Memory Bank</h1>
          <p className="text-xs text-slate-400 mt-1">Configure workspace rules and context vectors that guide model reasoning dynamically.</p>
        </div>
        
        {/* Toggle Controls */}
        <div className="flex items-center gap-4">
          <div className="bg-slate-950 border border-slate-900 rounded-lg p-0.5 flex">
            <button
              onClick={() => setActiveTab("graph")}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer ${
                activeTab === "graph" ? "bg-pink-500 text-white shadow-lg shadow-pink-500/10" : "text-slate-400 hover:text-white"
              }`}
            >
              Memory Graph
            </button>
            <button
              onClick={() => setActiveTab("ledger")}
              className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer ${
                activeTab === "ledger" ? "bg-blue-600 text-white shadow-lg shadow-blue-500/10" : "text-slate-400 hover:text-white"
              }`}
            >
              Memory Ledger
            </button>
          </div>
          <div className="hidden md:block text-xs font-mono text-slate-400 border-l border-slate-800 pl-4">
            Indexed: {memories.length} rules
          </div>
        </div>
      </div>

      {activeTab === "graph" ? (
        <NeuralNetworkGraph memories={memories} agents={agents} projects={projects} />
      ) : (
        /* Grid: Left - memory form, Right - memories list */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Memory creation card */}
          <div className="lg:col-span-1 glass-panel p-5 rounded-xl border border-slate-800/60 h-fit space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono">
              <PlusCircle className="w-4 h-4 text-purple-400" />
              <span className="font-bold uppercase text-slate-400">Index Custom Rule</span>
            </div>

            <form onSubmit={handleAddMemory} className="space-y-4 text-xs">
              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Context Statement</label>
                <textarea
                  required
                  placeholder="Declare system preference (e.g. 'Always write email drafts in professional, warm voice.')"
                  value={newMemoryText}
                  onChange={(e) => setNewMemoryText(e.target.value)}
                  className="w-full glass-input px-3 py-2 text-xs h-24 resize-none"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Neuron Category</label>
                <select
                  value={newMemoryType}
                  onChange={(e) => setNewMemoryType(e.target.value as any)}
                  className="w-full glass-input px-3 py-2 text-xs"
                >
                  <option value="user_preference">User Preference</option>
                  <option value="project_fact">Project Fact</option>
                  <option value="writing_style">Writing Style</option>
                  <option value="relationship">Relationship</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-mono text-slate-500 uppercase font-semibold mb-1">Semantic Weight (Stars)</label>
                <div className="flex items-center gap-1.5 pt-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setNewMemoryStars(star)}
                      className="cursor-pointer"
                    >
                      <Star
                        className={`w-5 h-5 ${
                          newMemoryStars >= star ? "text-amber-400 fill-amber-400/20" : "text-slate-600 hover:text-slate-500"
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 rounded-lg font-bold text-white transition-colors cursor-pointer"
              >
                Write to Neural Memory
              </button>
            </form>
          </div>

          {/* Memories list */}
          <div className="lg:col-span-2 space-y-4">
            {/* Search box */}
            <div className="relative">
              <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Fuzzy search synapses or labels..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full glass-input pl-10 pr-4 py-2.5 text-xs h-10"
              />
            </div>

            {/* Table list */}
            <div className="space-y-2">
              {filteredMemories.map((m) => {
                const getBadgeStyles = () => {
                  switch (m.type) {
                    case "user_preference": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
                    case "writing_style": return "bg-purple-500/10 text-purple-400 border-purple-500/20";
                    case "project_fact": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
                    default: return "bg-slate-800 text-slate-400 border-slate-700/50";
                  }
                };

                return (
                  <div
                    key={m.id}
                    className="p-3.5 bg-slate-900/40 border border-slate-850 hover:border-slate-800 rounded-xl flex items-center justify-between gap-4 transition-all text-xs"
                  >
                    <div className="space-y-1.5 min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[9px] font-mono border px-2 py-0.5 rounded uppercase font-semibold ${getBadgeStyles()}`}>
                          {m.type.replace("_", " ")}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">Recorded: {m.timestamp}</span>
                      </div>
                      <p className="text-slate-200 font-medium leading-relaxed font-sans">{m.text}</p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      {/* 5-star rater */}
                      <div className="flex items-center gap-0.5">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            onClick={() => handleAdjustStars(m.id, star)}
                            className="cursor-pointer"
                          >
                            <Star
                              className={`w-3.5 h-3.5 ${
                                m.importance >= star ? "text-amber-400 fill-amber-400/10" : "text-slate-700 hover:text-slate-500"
                              }`}
                            />
                          </button>
                        ))}
                      </div>

                      <button
                        onClick={() => handleDeleteMemory(m.id)}
                        className="p-1 text-slate-500 hover:text-red-400 rounded hover:bg-slate-850/60 transition-colors cursor-pointer"
                        title="Sever connection"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
