import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  Command,
  LayoutDashboard,
  MessageSquare,
  FolderKanban,
  Bot,
  Globe,
  Settings,
  Trash2,
  Play
} from "lucide-react";
import { WorkspaceView } from "../types";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  setCurrentView: (view: WorkspaceView) => void;
  triggerNotification: (title: string, msg: string, type: any) => void;
  toggleVoiceOrb: () => void;
}

export default function CommandPalette({
  isOpen,
  onClose,
  setCurrentView,
  triggerNotification,
  toggleVoiceOrb,
}: CommandPaletteProps) {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const modalRef = useRef<HTMLDivElement | null>(null);

  const commands = [
    { name: "Navigate to Dashboard / Command Center", action: () => { setCurrentView("dashboard"); triggerNotification("Viewport Switch", "Switched to central command metrics.", "info"); }, icon: LayoutDashboard, category: "Navigation" },
    { name: "Navigate to JARVIS AI Terminal (Chat)", action: () => { setCurrentView("chat"); triggerNotification("Viewport Switch", "Vocal and text chat streams loaded.", "info"); }, icon: MessageSquare, category: "Navigation" },
    { name: "Navigate to Workspace Manager (Projects)", action: () => { setCurrentView("projects"); triggerNotification("Viewport Switch", "Projects database loaded.", "info"); }, icon: FolderKanban, category: "Navigation" },
    { name: "Navigate to Agent Workforce (Orchestrator)", action: () => { setCurrentView("agents"); triggerNotification("Viewport Switch", "Loaded workforce cockpit.", "info"); }, icon: Bot, category: "Navigation" },
    { name: "Navigate to Autonomous Browser Manager", action: () => { setCurrentView("browser"); triggerNotification("Viewport Switch", "Autonomous browser timeline loaded.", "info"); }, icon: Globe, category: "Navigation" },
    { name: "Navigate to System Settings", action: () => { setCurrentView("settings"); triggerNotification("Viewport Switch", "System configurations loaded.", "info"); }, icon: Settings, category: "Navigation" },
    { name: "Initiate Voice Sync (Microphone mode)", action: () => { toggleVoiceOrb(); }, icon: Play, category: "AI Control" },
    { name: "Clean Workspace Temporary Cache Buffer", action: () => { triggerNotification("System Maintained", "Wiped 430MB cache allocations successfully.", "success"); }, icon: Trash2, category: "Maintenance" },
  ];

  const filtered = commands.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.category.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    // Reset selected index when search changes
    setSelectedIndex(0);
  }, [search]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
          onClose();
        }
      } else if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filtered, selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-start justify-center pt-24 px-4 animate-fade-in">
      {/* Backdrop overlay closer */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Palette Container */}
      <div
        ref={modalRef}
        className="w-full max-w-xl bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col z-10 max-h-[420px]"
      >
        {/* Search header bar */}
        <div className="px-4 py-3.5 border-b border-slate-900 flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-500" />
          <input
            type="text"
            autoFocus
            placeholder="Type a system command or search viewports..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 focus:outline-none text-sm font-sans"
          />
          <kbd className="font-mono text-[9px] px-2 py-0.5 bg-slate-900 border border-slate-800 rounded text-slate-500">ESC</kbd>
        </div>

        {/* Results Container */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-slate-600 text-xs font-mono">No matching system commands registered.</div>
          ) : (
            filtered.map((c, idx) => {
              const Icon = c.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={idx}
                  onClick={() => {
                    c.action();
                    onClose();
                  }}
                  className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-left transition-all text-xs cursor-pointer ${
                    isSelected
                      ? "bg-blue-600/10 border border-blue-500/30 text-white font-semibold"
                      : "border border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isSelected ? "text-blue-400" : "text-slate-500"}`} />
                    <span>{c.name}</span>
                  </div>

                  <span className="text-[9px] font-mono bg-slate-900 border border-slate-850 px-2 py-0.5 rounded text-slate-500 uppercase">
                    {c.category}
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* Footer shortcuts info */}
        <div className="px-4 py-2.5 bg-slate-950 border-t border-slate-900 flex items-center justify-between text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-1.5">
            <span>↑↓ to navigate</span>
            <span>•</span>
            <span>Enter to execute</span>
          </div>
          <span>⌘K to toggle palette</span>
        </div>

      </div>
    </div>
  );
}
