import React, { useState } from "react";
import {
  Settings,
  Sliders,
  ShieldCheck,
  Bell,
  HelpCircle,
  Key,
  Database,
  Moon,
  Sun,
  Lock,
  Keyboard,
  CheckCircle2,
  AlertCircle
} from "lucide-react";

interface SettingsViewProps {
  theme: "dark" | "light";
  toggleTheme: () => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  triggerNotification: (title: string, msg: string, type: any) => void;
  ttsEnabled?: boolean;
  setTtsEnabled?: (val: boolean) => void;
  sfxEnabled?: boolean;
  setSfxEnabled?: (val: boolean) => void;
}

export default function SettingsView({
  theme,
  toggleTheme,
  selectedModel,
  setSelectedModel,
  triggerNotification,
  ttsEnabled = true,
  setTtsEnabled,
  sfxEnabled = true,
  setSfxEnabled,
}: SettingsViewProps) {
  const [micPerm, setMicPerm] = useState(true);
  const [notifPerm, setNotifPerm] = useState(true);
  const [hasCheckedKey, setHasCheckedKey] = useState<boolean | null>(null);

  // Check if API key is loaded
  React.useEffect(() => {
    fetch("/api/config")
      .then(res => res.json())
      .then(data => setHasCheckedKey(data.hasApiKey))
      .catch(() => setHasCheckedKey(false));
  }, []);

  const handleTogglePermissions = (type: "mic" | "notif") => {
    if (type === "mic") {
      setMicPerm(!micPerm);
      triggerNotification("Permissions Updated", `Microphone permissions: ${!micPerm ? "GRANTED" : "REVOKED"}`, "info");
    } else {
      setNotifPerm(!notifPerm);
      triggerNotification("Permissions Updated", `Telemetry notifications: ${!notifPerm ? "GRANTED" : "REVOKED"}`, "info");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
      
      {/* Page Header */}
      <div className="pb-4 border-b border-slate-800/40">
        <h1 className="text-xl font-display font-bold text-white tracking-wide mt-0.5">Settings</h1>
        <p className="text-xs text-slate-400 mt-1">Configure intelligence model defaults, permissions, and environment setup.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 text-xs">
        
        {/* Left 2 Columns: Config Panels */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Cognitive engine defaults */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-4">
            <div className="flex items-center gap-2 font-mono text-xs text-white">
              <Sliders className="w-4 h-4 text-purple-400" />
              <span className="font-bold uppercase tracking-wider">Cognitive Engine Core</span>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Select which Gemini engine to use by default for multi-turn conversational reasoning, tool calling, and automation parses.
            </p>

            <div className="space-y-2">
              {[
                { id: "gemini-3.1-flash-lite", name: "Gemini 3.1 Flash Lite", desc: "Optimized for speed and minimal interaction latencies (Recommended)", badge: "Low Latency" },
                { id: "gemini-3.5-flash", name: "Gemini 3.5 Flash", desc: "General-purpose speed and high accuracy", badge: "Standard" },
                { id: "deepseek/deepseek-v4-flash", name: "Deepseek v4 Flash", desc: "Super fast Deepseek flash backup", badge: "OpenRouter" },
                { id: "gemma-4-31b", name: "Gemma 4 31b", desc: "Google Gemma 2 27B IT backup", badge: "OpenRouter" }
              ].map(model => (
                <div
                  key={model.id}
                  onClick={() => {
                    setSelectedModel(model.id);
                    triggerNotification("Cognitive Shift", `Rerouted pipeline default to ${model.name}.`, "success");
                  }}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${
                    selectedModel === model.id
                      ? "bg-blue-600/10 border-blue-500/40"
                      : "bg-transparent border-slate-850 hover:bg-slate-900/30"
                  }`}
                >
                  <div className="space-y-0.5">
                    <span className="font-bold text-slate-200 block">{model.name}</span>
                    <span className="text-[10px] text-slate-500 block">{model.desc}</span>
                  </div>

                  <span className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    selectedModel === model.id ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "bg-slate-800 text-slate-400"
                  }`}>
                    {model.badge}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Secure Environment credentials */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-4">
            <div className="flex items-center gap-2 font-mono text-xs text-white">
              <Key className="w-4 h-4 text-blue-400" />
              <span className="font-bold uppercase tracking-wider">Credential Verification (Settings Secrets)</span>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Your API keys and authorization secrets are managed securely by the container environment. Never commit actual secrets into source code repositories.
            </p>

            <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-slate-400 text-[11px]">GEMINI_API_KEY Connection:</span>
                {hasCheckedKey ? (
                  <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>VERIFIED ACTIVE</span>
                  </span>
                ) : hasCheckedKey === false ? (
                  <span className="text-[10px] font-mono font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                    <span>MISSING KEY</span>
                  </span>
                ) : (
                  <span className="text-[10px] font-mono font-bold text-slate-500 animate-pulse">Checking credentials...</span>
                )}
              </div>

              <div className="p-2.5 bg-slate-950/60 border border-slate-900 rounded-lg text-[10px] text-slate-500 leading-relaxed font-mono">
                💡 <strong className="text-slate-300">How to authorize:</strong> Click the <strong className="text-slate-300">Secrets</strong> panel in the left sidebar configuration tools, and specify the variable name <strong className="text-blue-400 font-bold">GEMINI_API_KEY</strong> with your real API token. JARVIS automatically reads the secrets securely at runtime.
              </div>
            </div>
          </div>

        </div>

        {/* Right 1 Column: Aesthetics, Permissions, Hotkeys info */}
        <div className="space-y-6">
          
          {/* Aesthetic Appearance */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-4">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold block">Aesthetics theme</span>
            
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Current active skin</span>
              <button
                onClick={toggleTheme}
                className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg font-bold text-white flex items-center gap-1.5 cursor-pointer transition-colors"
              >
                {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                <span className="capitalize">{theme} Theme</span>
              </button>
            </div>
          </div>

          {/* System Permissions toggle */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-4">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold block">System Permissions</span>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Microphone Vocal Sync</span>
                <button
                  onClick={() => handleTogglePermissions("mic")}
                  className={`w-10 h-5.5 rounded-full p-0.5 transition-colors cursor-pointer ${
                    micPerm ? "bg-blue-600" : "bg-slate-800"
                  }`}
                >
                  <div className={`w-4.5 h-4.5 bg-white rounded-full transition-transform ${
                    micPerm ? "translate-x-4.5" : "translate-x-0"
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400">Active Telemetry Logs</span>
                <button
                  onClick={() => handleTogglePermissions("notif")}
                  className={`w-10 h-5.5 rounded-full p-0.5 transition-colors cursor-pointer ${
                    notifPerm ? "bg-blue-600" : "bg-slate-800"
                  }`}
                >
                  <div className={`w-4.5 h-4.5 bg-white rounded-full transition-transform ${
                    notifPerm ? "translate-x-4.5" : "translate-x-0"
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between border-t border-slate-800/40 pt-3">
                <span className="text-slate-400">Talk-Back Engine (TTS)</span>
                <button
                  onClick={() => {
                    setTtsEnabled?.(!ttsEnabled);
                    triggerNotification("Audio Preference", `Talk-Back Speech: ${!ttsEnabled ? "ENABLED" : "MUTED"}`, "info");
                  }}
                  className={`w-10 h-5.5 rounded-full p-0.5 transition-colors cursor-pointer ${
                    ttsEnabled ? "bg-blue-600" : "bg-slate-800"
                  }`}
                >
                  <div className={`w-4.5 h-4.5 bg-white rounded-full transition-transform ${
                    ttsEnabled ? "translate-x-4.5" : "translate-x-0"
                  }`} />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400">Synthesizer Sound Effects (SFX)</span>
                <button
                  onClick={() => {
                    setSfxEnabled?.(!sfxEnabled);
                    triggerNotification("Audio Preference", `Sci-Fi Sound Effects: ${!sfxEnabled ? "ENABLED" : "SILENT"}`, "info");
                  }}
                  className={`w-10 h-5.5 rounded-full p-0.5 transition-colors cursor-pointer ${
                    sfxEnabled ? "bg-blue-600" : "bg-slate-800"
                  }`}
                >
                  <div className={`w-4.5 h-4.5 bg-white rounded-full transition-transform ${
                    sfxEnabled ? "translate-x-4.5" : "translate-x-0"
                  }`} />
                </button>
              </div>
            </div>
          </div>

          {/* Keyboard Hotkeys directory */}
          <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-3">
            <div className="flex items-center gap-2 text-slate-400 font-mono">
              <Keyboard className="w-4 h-4 text-blue-400" />
              <span className="font-bold uppercase">Keyboard shortcuts</span>
            </div>

            <div className="space-y-2 pt-1">
              {[
                { shortcut: "Ctrl + K", action: "Toggle Command Palette" },
                { shortcut: "Shift + Enter", action: "New line in chat prompt" },
                { shortcut: "ESC", action: "Close active overlays" }
              ].map((hk, idx) => (
                <div key={idx} className="flex justify-between items-center text-[11px]">
                  <span className="text-slate-400">{hk.action}</span>
                  <kbd className="font-mono bg-slate-900 border border-slate-800/80 px-2 py-0.5 rounded text-slate-500 text-[10px]">{hk.shortcut}</kbd>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
