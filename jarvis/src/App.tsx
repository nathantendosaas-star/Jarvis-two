import React, { Suspense, lazy, useState, useEffect, useRef } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import HUDView from "./components/HUDView";
import CommandPalette from "./components/CommandPalette";
import VoiceSync from "./components/VoiceSync";
import { fetchWorkspaceData, fetchWorkspaceFiles, fetchAgents, updateAgent as apiUpdateAgent, deleteAgent as apiDeleteAgent, createAgent as apiCreateAgent } from "./api";
import { audioService } from "./utils/audioService";

import {
  WorkspaceView,
  Project,
  Agent,
  FileNode,
  BrowserTab,
  MemoryItem,
  WorkflowNode,
  ChatMessage,
  SystemNotification,
  SystemMetrics
} from "./types";

const ChatView = lazy(() => import("./components/ChatView"));
const ProjectsView = lazy(() => import("./components/ProjectsView"));
const AgentsView = lazy(() => import("./components/AgentsView"));
const FilesView = lazy(() => import("./components/FilesView"));
const BrowserView = lazy(() => import("./components/BrowserView"));
const MemoryView = lazy(() => import("./components/MemoryView"));
const AutomationView = lazy(() => import("./components/AutomationView"));
const SettingsView = lazy(() => import("./components/SettingsView"));

export default function App() {
  const [booted, setBooted] = useState(() => {
    return sessionStorage.getItem("jarvis-booted") === "true";
  });

  const handleBoot = () => {
    sessionStorage.setItem("jarvis-booted", "true");
    setBooted(true);
    audioService.playBootSound();
    setTimeout(() => {
      audioService.speak("Welcome back, sir.");
      triggerNotification("System Online", "Welcome back, sir.", "success");
    }, 120);
  };

  const [currentView, setCurrentView] = useState<WorkspaceView>("dashboard");
  const [collapsed, setCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gemini-3.1-flash-lite");

  // Audio & Mic Volume States
  const [ttsEnabled, setTtsEnabledState] = useState(() => {
    return localStorage.getItem("jarvis-tts-enabled") !== "false";
  });
  const [sfxEnabled, setSfxEnabledState] = useState(() => {
    return localStorage.getItem("jarvis-sfx-enabled") !== "false";
  });
  const [isMicActive, setIsMicActive] = useState(false);
  const [micVolume, setMicVolume] = useState(0);

  const setTtsEnabled = (val: boolean) => {
    setTtsEnabledState(val);
    audioService.setTtsEnabled(val);
  };

  const setSfxEnabled = (val: boolean) => {
    setSfxEnabledState(val);
    audioService.setSfxEnabled(val);
  };

  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const handleMicActiveChange = (active: boolean, stream?: MediaStream) => {
    setIsMicActive(active);

    if (!active) {
      setMicVolume(0);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      analyserRef.current = null;
      audioService.playMicCloseSound();
      return;
    }

    // Play active chirp
    audioService.playMicOpenSound();

    if (stream) {
      try {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioCtx = new AudioContextClass();
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        audioCtxRef.current = audioCtx;
        analyserRef.current = analyser;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const updateVolume = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteTimeDomainData(dataArray);

          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            const v = (dataArray[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / bufferLength);

          // Map RMS to a pleasant visual pulse range: 0 to 1
          const smoothedVolume = Math.min(1, rms * 4);
          setMicVolume(smoothedVolume);

          animationFrameRef.current = requestAnimationFrame(updateVolume);
        };

        updateVolume();
      } catch (err) {
        console.warn("Failed to start mic volume analyser context:", err);
      }
    }
  };

  const [dataStatus, setDataStatus] = useState<"loading" | "ready" | "error">("loading");

  // UI Open / Close Triggers
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Global Workspace states
  const [projects, setProjects] = useState<Project[]>([]);

  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [files, setFiles] = useState<FileNode[]>([]);
  const [tabs, setTabs] = useState<BrowserTab[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);
  const [pendingVoicePrompt, setPendingVoicePrompt] = useState<string | null>(null);

  const unreadCount = notifications.filter(n => !n.read).length;

  const triggerNotification = (title: string, message: string, type: "info" | "success" | "warning" | "error" | "agent" = "info") => {
    const newNotif: SystemNotification = {
      id: "n-" + Date.now(),
      title,
      message,
      type,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      read: false
    };
    setNotifications(prev => [newNotif, ...prev]);
  };

  const workspaceReloadTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const refresh = () => {
      if (workspaceReloadTimer.current) clearTimeout(workspaceReloadTimer.current);
      workspaceReloadTimer.current = setTimeout(() => { void reloadWorkspaceData(); }, 150);
    };
    window.addEventListener("jarvis:workspace-changed", refresh);
    return () => {
      window.removeEventListener("jarvis:workspace-changed", refresh);
      if (workspaceReloadTimer.current) clearTimeout(workspaceReloadTimer.current);
    };
  }, []);

  useEffect(() => {
    const handleNotification = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        const { title, message, type } = customEvent.detail;
        triggerNotification(title, message, type);
      }
    };
    window.addEventListener("jarvis:notification", handleNotification);
    return () => {
      window.removeEventListener("jarvis:notification", handleNotification);
    };
  }, []);

  const reloadWorkspaceData = async () => {
    setDataStatus("loading");
    try {
      const [{ projects: loadedProjects }, workspaceFiles, loadedAgents] = await Promise.all([
        fetchWorkspaceData(),
        fetchWorkspaceFiles(),
        fetchAgents().catch(() => []),   // agents table may be empty on first boot
      ]);
      setProjects(loadedProjects);
      setFiles(workspaceFiles);
      setAgents(loadedAgents);
      setDataStatus("ready");
    } catch (error) {
      setDataStatus("error");
      triggerNotification(
        "Data Sync Failed",
        error instanceof Error ? error.message : "Unable to load backend workspace data.",
        "error",
      );
    }
  };

  // Persist agent mutations to the backend and sync local state
  const handleUpdateAgent = async (
    agentId: string,
    patch: { status?: string; priority?: string; cpu_allocation?: number; memory_allocation?: number; current_task?: string | null; activity?: string[] }
  ) => {
    try {
      const updated = await apiUpdateAgent(agentId, patch);
      setAgents(prev => prev.map(a => (a.id === agentId ? updated : a)));
    } catch {
      triggerNotification("Agent Sync Failed", "Could not persist agent update to backend.", "error");
    }
  };

  const handleDeleteAgent = async (agentId: string, deleteCache: boolean = false) => {
    try {
      await apiDeleteAgent(agentId, deleteCache);
      setAgents(prev => prev.filter(a => a.id !== agentId));
      triggerNotification("Agent Decommissioned", "The agent has been successfully removed from workforce.", "success");
    } catch {
      triggerNotification("Agent Decommission Failed", "Could not remove the agent.", "error");
    }
  };

  const handleCreateAgent = async (data: {
    name: string;
    role: string;
    avatar?: string;
    capabilities?: string[];
    tools?: string[];
  }) => {
    try {
      const created = await apiCreateAgent(data);
      setAgents(prev => [created, ...prev]);
      triggerNotification("Agent Created", `${data.name} is now active with cached context.`, "success");
    } catch {
      triggerNotification("Agent Creation Failed", "Could not persist new agent.", "error");
    }
  };

  useEffect(() => {
    reloadWorkspaceData();
  }, []);

  // Keyboard shortcut listener for Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandOpen(prev => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const toggleCommandPalette = () => setIsCommandOpen(!isCommandOpen);
  const toggleVoiceOrb = () => setIsVoiceOpen(!isVoiceOpen);
  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    triggerNotification("Aesthetics Toggle", `Theme shifted to ${nextTheme} skin.`, "info");
  };

  // Handles transcribed text from the voice sync orb overlay
  const handleVoiceTranscriptionResult = (transcribedText: string) => {
    setPendingVoicePrompt(transcribedText);
    setCurrentView("chat"); // Reroute user to chat viewport
    triggerNotification("Sync Complete", "Voice input pushed to active chat.", "success");
  };

  const getActiveProjectName = () => {
    if (!activeProjectId) return null;
    return projects.find(p => p.id === activeProjectId)?.name || null;
  };

  const workspaceStorageBytes = projects.reduce((total, project) => total + (project.storageBytes || 0), 0);
  const workspaceFileCount = projects.reduce((total, project) => total + (project.fileCount || 0), 0);
  const workspaceTaskCount = projects.reduce((total, project) => total + project.tasksCount, 0);

  const systemMetrics: SystemMetrics = {
    cpu: projects.length,
    ram: Number((workspaceStorageBytes / (1024 * 1024)).toFixed(2)),
    networkSpeed: workspaceFileCount,
    storage: workspaceTaskCount,
    apiCalls: notifications.length,
    activeAgents: agents.filter(a => a.status === 'working').length
  };

  const routeFallback = (
    <div className="flex h-full items-center justify-center text-sm text-slate-400">
      Loading workspace...
    </div>
  );

  return (
    <div className={`min-h-screen flex text-slate-100 font-sans selection:bg-blue-500/20 overflow-hidden ${
      theme === "dark" ? "bg-jarvis-bg" : "bg-slate-50 text-slate-900"
    }`}>
      
      {/* Dynamic Background visual vectors (Iron Man ARC Reactor or minimal stars) */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-blue-600/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-600/[0.03] rounded-full blur-[100px]" />
      </div>

      {/* Primary Sidebar */}
      <Sidebar
        currentView={currentView}
        setCurrentView={(view) => {
          setCurrentView(view);
          setIsMobileMenuOpen(false);
        }}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        projects={projects}
        activeProjectId={activeProjectId}
        setActiveProjectId={setActiveProjectId}
        toggleCommandPalette={toggleCommandPalette}
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Main viewport area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden z-10 relative">
        {/* Top telemetry bar */}
        <TopBar
          currentView={currentView}
          activeProjectName={getActiveProjectName()}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          notifications={notifications}
          toggleCommandPalette={toggleCommandPalette}
          toggleVoiceOrb={toggleVoiceOrb}
          theme={theme}
          toggleTheme={toggleTheme}
          metrics={systemMetrics}
          unreadCount={unreadCount}
          setNotifications={setNotifications}
          toggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        {/* Dynamic workspace viewport routing */}
        <main className="flex-1 overflow-hidden flex flex-col">
          {currentView === "dashboard" && (
            <HUDView
              projects={projects}
              agents={agents}
              metrics={systemMetrics}
              messages={messages}
              setMessages={setMessages}
              triggerNotification={triggerNotification}
              selectedModel={selectedModel}
              onOpenVoice={toggleVoiceOrb}
              isMicActive={isMicActive}
              micVolume={micVolume}
              ttsEnabled={ttsEnabled}
              setTtsEnabled={setTtsEnabled}
              sfxEnabled={sfxEnabled}
              setSfxEnabled={setSfxEnabled}
            />
          )}

          <Suspense fallback={routeFallback}>
            {currentView === "chat" && (
              <ChatView
                messages={messages}
                setMessages={setMessages}
                selectedModel={selectedModel}
                triggerNotification={triggerNotification}
                pendingVoicePrompt={pendingVoicePrompt}
                clearPendingVoicePrompt={() => setPendingVoicePrompt(null)}
                onMicActiveChange={handleMicActiveChange}
                systemInstruction="You are JARVIS, an advanced AI Operating System. Speak confidently, professionally, yet warm. Act as the central nervous orchestrator of specialized agents."
              />
            )}

            {currentView === "projects" && (
              <ProjectsView
                projects={projects}
                setProjects={setProjects}
                activeProjectId={activeProjectId}
                setActiveProjectId={setActiveProjectId}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "agents" && (
              <AgentsView
                agents={agents}
                setAgents={setAgents}
                onUpdateAgent={handleUpdateAgent}
                onDeleteAgent={handleDeleteAgent}
                onCreateAgent={handleCreateAgent}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "files" && (
              <FilesView
                files={files}
                setFiles={setFiles}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "browser" && (
              <BrowserView
                tabs={tabs}
                setTabs={setTabs}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "memory" && (
              <MemoryView
                memories={memories}
                setMemories={setMemories}
                agents={agents}
                projects={projects}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "automation" && (
              <AutomationView
                nodes={nodes}
                setNodes={setNodes}
                triggerNotification={triggerNotification}
              />
            )}

            {currentView === "settings" && (
              <SettingsView
                theme={theme}
                toggleTheme={toggleTheme}
                selectedModel={selectedModel}
                setSelectedModel={setSelectedModel}
                triggerNotification={triggerNotification}
                ttsEnabled={ttsEnabled}
                setTtsEnabled={setTtsEnabled}
                sfxEnabled={sfxEnabled}
                setSfxEnabled={setSfxEnabled}
              />
            )}
          </Suspense>
        </main>
      </div>

      {/* Floating command palette overlay */}
      <CommandPalette
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
        setCurrentView={setCurrentView}
        triggerNotification={triggerNotification}
        toggleVoiceOrb={toggleVoiceOrb}
      />

      {/* Voice Sync interactive overlay orb */}
      <VoiceSync
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        onTranscriptionResult={handleVoiceTranscriptionResult}
        triggerNotification={triggerNotification}
        onMicActiveChange={handleMicActiveChange}
      />

      {/* Welcome Core Boot-Up Overlay */}
      {!booted && (
        <div className="fixed inset-0 bg-[#06070a] z-[9999] flex flex-col items-center justify-center p-6 text-center select-none font-mono">
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/[0.04] rounded-full blur-[150px]" />
          </div>

          <div className="relative flex flex-col items-center max-w-md w-full gap-8">
            {/* Glowing Core Visual */}
            <div className="relative w-32 h-32 flex items-center justify-center">
              <div className="absolute inset-0 border border-slate-800 rounded-full animate-hud-spin-slow" />
              <div className="absolute inset-2 border border-dashed border-blue-500/30 rounded-full animate-hud-spin-reverse" />
              <div className="absolute inset-6 border-[3px] border-blue-500/20 rounded-full animate-hud-pulse" />
              <div className="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/50 flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.3)] animate-pulse">
                <div className="w-2.5 h-2.5 bg-blue-400 rounded-full" />
              </div>
            </div>

            {/* Typography */}
            <div className="space-y-2">
              <h2 className="text-xl font-display font-bold text-white tracking-[0.25em]">JARVIS OS</h2>
              <p className="text-[10px] text-slate-500 tracking-wider uppercase">COGNITIVE NETWORK INTERLINK</p>
            </div>

            {/* Button */}
            <button
              onClick={handleBoot}
              className="px-6 py-3 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/40 hover:border-blue-500 rounded-xl text-xs font-bold text-blue-400 hover:text-white transition-all cursor-pointer shadow-lg hover:shadow-[0_0_25px_rgba(59,130,246,0.15)] uppercase tracking-widest"
            >
              Initialize Link
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
