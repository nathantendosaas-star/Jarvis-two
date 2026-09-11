import React, { useState, useEffect } from "react";
import {
  Search,
  Mic,
  Bell,
  Sun,
  Moon,
  ChevronDown,
  Menu
} from "lucide-react";
import { SystemMetrics, SystemNotification, WorkspaceView } from "../types";

interface TopBarProps {
  currentView: WorkspaceView;
  activeProjectName: string | null;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  notifications: SystemNotification[];
  toggleCommandPalette: () => void;
  toggleVoiceOrb: () => void;
  theme: "dark" | "light";
  toggleTheme: () => void;
  metrics: SystemMetrics;
  unreadCount: number;
  setNotifications: React.Dispatch<React.SetStateAction<SystemNotification[]>>;
  toggleMobileMenu?: () => void;
}

export default function TopBar({
  currentView,
  activeProjectName,
  selectedModel,
  setSelectedModel,
  notifications,
  toggleCommandPalette,
  toggleVoiceOrb,
  theme,
  toggleTheme,
  unreadCount,
  setNotifications,
  toggleMobileMenu,
}: TopBarProps) {
  const [time, setTime] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  useEffect(() => {
    // Live ticking clock
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    };
    updateTime();
    const clockInterval = setInterval(updateTime, 1000);

    return () => {
      clearInterval(clockInterval);
    };
  }, []);

  const models = [
    { id: "gemini-3.1-flash-lite", name: "Gemini 3.1 Flash Lite", desc: "Super-fast, low-latency", badge: "Ultra Speed" },
    { id: "gemini-3.5-flash", name: "Gemini 3.5 Flash", desc: "General & fast tasks", badge: "Balanced" },
    { id: "deepseek/deepseek-v4-flash", name: "Deepseek v4 Flash", desc: "Super fast Deepseek flash", badge: "OpenRouter" },
    { id: "gemma-4-31b", name: "Gemma 4 31b", desc: "Google Gemma 2 27B IT", badge: "OpenRouter" },
  ];

  const getFriendlyViewName = () => {
    if (activeProjectName) return activeProjectName;
    switch (currentView) {
      case "dashboard": return "Dashboard";
      case "chat": return "AI Chat";
      case "projects": return "Workspaces";
      case "agents": return "Agents";
      case "files": return "Files";
      case "browser": return "Web Browser";
      case "memory": return "Memory Bank";
      case "automation": return "Automations";
      case "settings": return "Settings";
      default: return "JARVIS";
    }
  };

  const handleClearNotifications = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  return (
    <header className="h-16 border-b border-slate-800/40 px-6 flex items-center justify-between glass-panel z-20 shrink-0">
      {/* Left: View title & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobileMenu}
          className="md:hidden p-1 -ml-2 text-slate-400 hover:text-white transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex flex-col">
          <h1 className="text-md font-display font-semibold text-white tracking-wide truncate w-[140px] sm:w-auto sm:max-w-xs md:max-w-md">
            {getFriendlyViewName()}
          </h1>
        </div>
      </div>

      {/* Center: Command input trigger */}
      <div className="hidden lg:flex items-center gap-2 max-w-md flex-1 mx-8">
        <button
          onClick={toggleCommandPalette}
          className="w-full flex items-center gap-3 px-4 py-2 bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800/70 hover:border-slate-700 rounded-full text-slate-400 text-xs transition-all duration-150 cursor-pointer shadow-inner shadow-black/20"
        >
          <Search className="w-4 h-4 text-slate-500" />
          <span className="text-left flex-1">Search anything or run command...</span>
          <div className="flex items-center gap-1 font-mono text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700/30">
            <span>Ctrl</span>
            <span>+</span>
            <span>K</span>
          </div>
        </button>
      </div>

      {/* Right: Model selector, Notification, Clock, Profile */}
      <div className="flex items-center gap-4 text-slate-300">

        {/* Model Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowModelDropdown(!showModelDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 rounded-lg text-xs font-mono text-slate-200 transition-all shadow-md cursor-pointer"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            <span className="hidden sm:inline text-slate-400">Model:</span>
            <span className="font-semibold text-white">
              {models.find(m => m.id === selectedModel)?.name.replace("Gemini ", "") || selectedModel}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showModelDropdown && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowModelDropdown(false)} />
              <div className="absolute right-0 mt-2 w-72 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl p-1 z-50 animate-fade-in">
                <div className="p-2 border-b border-slate-800/60 mb-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-bold">Select Intelligence Model</span>
                </div>
                {models.map(m => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedModel(m.id);
                      setShowModelDropdown(false);
                    }}
                    className={`w-full flex flex-col p-2.5 text-left rounded-lg transition-all text-xs border cursor-pointer ${
                      selectedModel === m.id
                        ? "bg-blue-600/10 border-blue-500/30 text-white"
                        : "border-transparent hover:bg-slate-900/60 text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full font-semibold">
                      <span>{m.name}</span>
                      <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${
                        "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      }`}>
                        {m.badge}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 mt-1 font-sans">{m.desc}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Floating Voice Orb Trigger */}
        <button
          onClick={toggleVoiceOrb}
          className="p-2 bg-slate-900/40 hover:bg-blue-600/10 border border-slate-800/80 hover:border-blue-500/30 rounded-lg text-slate-400 hover:text-blue-400 transition-all cursor-pointer shadow group"
          title="Voice Command"
        >
          <Mic className="w-4 h-4" />
        </button>

        {/* Notifications Tray */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 bg-slate-900/40 hover:bg-slate-800/80 border border-slate-800/80 hover:border-slate-700 rounded-lg text-slate-400 hover:text-white transition-all cursor-pointer shadow relative"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-red-500 text-white font-mono text-[9px] font-bold h-4 w-4 rounded-full flex items-center justify-center border border-slate-950">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNotifications(false)} />
              <div className="absolute right-0 mt-2 w-80 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl p-1 z-50 max-h-96 flex flex-col">
                <div className="p-3 border-b border-slate-800/60 flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-white uppercase">System Notifications</span>
                  <button
                    onClick={handleClearNotifications}
                    className="text-[10px] text-blue-400 hover:text-blue-300 font-semibold cursor-pointer"
                  >
                    Dismiss All
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-slate-500 text-xs">No notifications.</div>
                  ) : (
                    notifications.map(n => (
                      <div
                        key={n.id}
                        className={`p-2.5 rounded-lg text-xs transition-all border ${
                          n.read ? "bg-transparent border-transparent text-slate-400" : "bg-slate-900/50 border-slate-800/40 text-slate-200"
                        }`}
                      >
                        <div className="flex items-center justify-between font-semibold mb-0.5">
                          <span className={`text-[11px] ${
                            n.type === 'error' ? "text-red-400" : n.type === 'warning' ? "text-amber-400" : n.type === 'success' ? "text-emerald-400" : "text-blue-400"
                          }`}>
                            {n.title}
                          </span>
                          <span className="text-[9px] font-mono text-slate-500">{n.time}</span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1">{n.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Live Clock */}
        <div className="hidden sm:flex font-mono text-xs font-bold text-slate-400 bg-slate-900/20 border border-slate-800/40 px-3 py-1.5 rounded-lg tracking-wider">
          {time}
        </div>

        {/* Theme button & Profile Avatar */}
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800/40 rounded-lg cursor-pointer transition-colors"
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-white shadow-md border border-slate-700/50 cursor-pointer">
          N
        </div>

      </div>
    </header>
  );
}
