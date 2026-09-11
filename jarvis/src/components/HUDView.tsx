import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Mic,
  Activity,
  Box,
  BarChart2,
  Clock,
  Terminal,
  Cpu,
  Globe,
  Settings,
  ShieldAlert,
  Send,
  User,
  Bot
} from "lucide-react";
import { Project, Agent, SystemMetrics, ChatMessage } from "../types";
import D3Timeline from "./D3Timeline";
import { audioService } from "../utils/audioService";

interface HUDViewProps {
  projects: Project[];
  agents: Agent[];
  metrics: SystemMetrics;
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  triggerNotification: (title: string, msg: string, type: any) => void;
  selectedModel: string;
  onOpenVoice: () => void;
  isMicActive?: boolean;
  micVolume?: number;
  ttsEnabled?: boolean;
  setTtsEnabled?: (val: boolean) => void;
  sfxEnabled?: boolean;
  setSfxEnabled?: (val: boolean) => void;
}

export default function HUDView({
  projects,
  agents,
  metrics,
  messages,
  setMessages,
  triggerNotification,
  selectedModel,
  onOpenVoice,
  isMicActive = false,
  micVolume = 0,
  ttsEnabled = true,
  setTtsEnabled,
  sfxEnabled = true,
  setSfxEnabled
}: HUDViewProps) {
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Memoize task volatility bar height calculations.
  // Previously, recalculating random values on every render pass caused layout shifts and recalculations.
  const volatilityBars = useMemo(() => {
    return Array.from({ length: 8 }, (_, i) => ({
      h1: Math.floor(Math.random() * 60) + 20,
      h2: Math.floor(Math.random() * 40) + 10,
      isGreen: i % 2 === 0
    }));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isProcessing) return;

    const userMsg = input.trim();
    setInput("");
    
    const newUserMsg: ChatMessage = {
      id: "msg-" + Date.now(),
      role: "user",
      content: userMsg,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, newUserMsg]);
    setIsProcessing(true);

    // Cancel any ongoing speech
    audioService.cancelSpeech();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          history: messages.slice(-10),
          model: selectedModel,
          useSearch: true
        })
      });

      if (!res.ok) throw new Error("API Error");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = "";
      let lastSpokenIndex = 0;
      
      const newBotMsgId = "msg-" + Date.now();
      setMessages(prev => [
        ...prev,
        { id: newBotMsgId, role: "model", content: "", timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      ]);

      while (reader) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });
        const lines = chunkText.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "");
            if (dataStr === "[DONE]") {
              setIsProcessing(false);
              break;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.error) {
                triggerNotification("System Error", data.error, "error");
                setIsProcessing(false);
                break;
              }
              if (data.text) {
                fullResponse += data.text;
                setMessages(prev => prev.map(m => m.id === newBotMsgId ? { ...m, content: fullResponse } : m));

                // Play subtle sci-fi typing click
                audioService.playTypingSound();

                // Speech synthesis sentence-by-sentence parsing
                const newText = fullResponse.slice(lastSpokenIndex);
                const sentenceEndRegex = /[.!?]+(\s+|$)/g;
                let match;
                let tempIndex = 0;

                while ((match = sentenceEndRegex.exec(newText)) !== null) {
                  const sentenceEnd = match.index + match[0].length;
                  const sentence = newText.slice(tempIndex, sentenceEnd).trim();
                  if (sentence) {
                    audioService.speak(sentence);
                  }
                  tempIndex = sentenceEnd;
                }
                lastSpokenIndex += tempIndex;
              }
            } catch (err) {
              console.error("Failed to parse SSE data", err);
            }
          }
        }
      }

      // Speak any remaining response that wasn't punctuated
      const remainingText = fullResponse.slice(lastSpokenIndex).trim();
      if (remainingText) {
        audioService.speak(remainingText);
      }
    } catch (err) {
      triggerNotification("Communication Failure", "Failed to reach cognitive core.", "error");
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen h-full bg-hud-bg overflow-y-auto text-slate-300 font-sans p-4 gap-4">
      {/* Top Bar - Minimal */}
      <div className="flex items-center justify-between px-2 text-[10px] uppercase font-mono tracking-widest text-slate-500">
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-hud-green animate-pulse" /> CORE_SYSTEM_ONLINE</span>
          <span>LAT: 12ms</span>
          <span>NET: SECURE</span>
        </div>
        <div className="flex items-center gap-6">
          <span>MODEL: {selectedModel.split("-").slice(0,2).join(" ").toUpperCase()}</span>
          <span>{new Date().toLocaleDateString()}</span>
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 min-h-0">
        
        {/* Left Column: Monitoring */}
        <div className="hidden md:flex flex-col col-span-3 gap-4">
          
          {/* Card 1: Audio Cognitive Interlink Toggles */}
          <div className="bg-hud-card rounded-3xl p-5 border border-white/5 flex flex-col gap-4 shadow-xl font-mono">
            <div className="flex justify-between items-center text-xs font-bold text-white uppercase tracking-wider">
              <span>COGNITIVE_AUDIO_LINK</span>
              <Activity className="w-4 h-4 text-hud-teal animate-pulse" />
            </div>

            <div className="space-y-4 pt-2">
              {/* Talk-Back Engine Switch */}
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-300 font-bold uppercase">TALK_BACK_TTS</span>
                  <span className="text-[9px] text-slate-500">Speech Output Engine</span>
                </div>
                <button
                  onClick={() => setTtsEnabled?.(!ttsEnabled)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                    ttsEnabled
                      ? "bg-hud-teal/10 border-hud-teal/30 text-hud-teal shadow-[0_0_10px_rgba(45,212,191,0.15)]"
                      : "bg-transparent border-white/5 text-slate-500"
                  }`}
                >
                  {ttsEnabled ? "SECURE_ON" : "MUTED"}
                </button>
              </div>

              {/* Synth SFX Switch */}
              <div className="flex items-center justify-between text-[11px] pt-2 border-t border-white/5">
                <div className="flex flex-col gap-0.5">
                  <span className="text-slate-300 font-bold uppercase">SYNTH_SFX</span>
                  <span className="text-[9px] text-slate-500">Sci-Fi Audio Feedback</span>
                </div>
                <button
                  onClick={() => setSfxEnabled?.(!sfxEnabled)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all cursor-pointer ${
                    sfxEnabled
                      ? "bg-hud-green/10 border-hud-green/30 text-hud-green shadow-[0_0_10px_rgba(163,230,53,0.15)]"
                      : "bg-transparent border-white/5 text-slate-500"
                  }`}
                >
                  {sfxEnabled ? "ONLINE" : "SILENT"}
                </button>
              </div>
            </div>
          </div>

          {/* Card 2: System Usage */}
          <div className="bg-hud-card rounded-3xl p-5 border border-white/5 flex flex-col gap-4 shadow-xl">
            <div className="flex justify-between items-center text-xs font-bold text-white uppercase tracking-wider">
              <span>System Core</span>
              <Cpu className="w-4 h-4 text-slate-500" />
            </div>
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-400">CPU LOAD</span>
                <span className="text-hud-yellow">{metrics.cpu}%</span>
              </div>
              <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden border border-white/5">
                <div className="bg-hud-yellow h-full" style={{ width: `${metrics.cpu}%` }} />
              </div>
              
              <div className="flex items-center justify-between text-[10px] font-mono mt-4">
                <span className="text-slate-400">MEMORY ALOC</span>
                <span className="text-hud-teal">{metrics.ram}GB</span>
              </div>
              <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden border border-white/5">
                <div className="bg-hud-teal h-full" style={{ width: `${(metrics.ram / 16) * 100}%` }} />
              </div>
            </div>
          </div>

          {/* Card 3: Agents */}
          <div className="bg-hud-card rounded-3xl p-5 border border-white/5 flex-1 shadow-xl flex flex-col overflow-hidden">
            <div className="flex justify-between items-center text-xs font-bold text-white uppercase tracking-wider mb-4">
              <span>Active Agents</span>
              <span className="bg-hud-green/20 text-hud-green px-2 py-0.5 rounded-full text-[10px]">{agents.length} Online</span>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {agents.map(a => (
                <div key={a.id} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-black border border-white/10 flex items-center justify-center text-sm">{a.avatar}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] text-white font-bold truncate">{a.name}</div>
                    <div className="text-[9px] text-slate-500 truncate">{a.status === "working" ? a.currentTask : a.role}</div>
                  </div>
                  <div className={`w-1.5 h-1.5 rounded-full ${a.status === "working" ? "bg-hud-green animate-pulse" : a.status === "paused" ? "bg-hud-orange" : "bg-slate-600"}`} />
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Center Column: The HUD / Agent Core */}
        <div className="col-span-1 md:col-span-6 flex flex-col relative h-full">
          
          {/* Futuristic HUD Background Element */}
          <div
            className="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden transition-opacity duration-300"
            style={{ opacity: isMicActive ? 0.35 : 0.2 }}
          >
            <div
              className="relative w-96 h-96 flex items-center justify-center transition-transform duration-75"
              style={{ transform: isMicActive ? `scale(${1 + micVolume * 0.4})` : 'scale(1)' }}
            >
              <div
                className="absolute inset-0 border-2 rounded-full animate-hud-spin transition-colors duration-150"
                style={{ borderColor: isMicActive ? 'var(--color-hud-teal)' : '#475569' }}
              />
              <div
                className="absolute inset-4 border border-dashed rounded-full animate-hud-spin-reverse transition-colors duration-150"
                style={{ borderColor: isMicActive ? 'var(--color-hud-green)' : '#64748b' }}
              />
              <div
                className="absolute inset-12 border-[4px] rounded-full animate-hud-pulse transition-all duration-75"
                style={{
                  borderColor: isMicActive ? 'var(--color-hud-green)' : 'rgba(45,212,191,0.3)',
                  borderWidth: isMicActive ? `${4 + micVolume * 8}px` : '4px'
                }}
              />
              
              {/* Center crosshairs */}
              <div className="absolute w-[120%] h-[1px] bg-slate-700/50" />
              <div className="absolute h-[120%] w-[1px] bg-slate-700/50" />
            </div>
          </div>

          {/* Chat Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 z-10 flex flex-col space-y-6">
            <div className="text-center mt-12 mb-8 animate-fade-in">
              <div
                className={`w-16 h-16 mx-auto bg-black border-2 rounded-full flex items-center justify-center mb-4 transition-all duration-75 ${
                  isMicActive ? "" : "animate-hud-pulse border-hud-teal shadow-[0_0_30px_rgba(45,212,191,0.2)]"
                }`}
                style={isMicActive ? {
                  transform: `scale(${1 + micVolume * 0.5})`,
                  borderColor: 'var(--color-hud-green)',
                  boxShadow: `0 0 ${30 + micVolume * 60}px rgba(163, 230, 53, ${0.3 + micVolume * 0.7})`
                } : undefined}
              >
                <Bot className={`w-8 h-8 transition-colors duration-150 ${isMicActive ? 'text-hud-green' : 'text-hud-teal'}`} />
              </div>
              <h1 className="text-2xl font-display font-bold text-white tracking-widest">
                {isMicActive ? "VOCAL_SYNC_ACTIVE" : "SYSTEM NEXUS"}
              </h1>
              <p className="text-xs text-slate-400 font-mono mt-2 uppercase tracking-wider">Awaiting plain english instruction</p>
            </div>

            {messages.map((msg, i) => (
              <div key={msg.id} className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}>
                <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center border border-white/10 bg-hud-card">
                  {msg.role === 'user' ? <User className="w-4 h-4 text-hud-green" /> : <Bot className="w-4 h-4 text-hud-teal" />}
                </div>
                <div className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase">
                    <span>{msg.role === 'user' ? 'OPERATOR' : 'JARVIS'}</span>
                    <span>{msg.timestamp}</span>
                  </div>
                  <div className={`p-4 text-sm leading-relaxed backdrop-blur-md border ${
                    msg.role === 'user' 
                      ? 'bg-hud-green/10 border-hud-green/20 text-hud-green rounded-2xl rounded-tr-sm' 
                      : 'bg-hud-card/80 border-white/10 text-slate-200 rounded-2xl rounded-tl-sm shadow-xl font-mono'
                  }`}>
                    {msg.content}
                    {msg.role === 'model' && isProcessing && i === messages.length - 1 && (
                      <span className="inline-block w-2 h-4 bg-hud-teal ml-1 animate-pulse" />
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} className="h-4" />
          </div>

          {/* Input Bar */}
          <div className="sticky bottom-0 z-30 bg-[#06070a]/95 backdrop-blur-md border-t border-slate-800/60 p-4 shrink-0">
            <form onSubmit={handleSend} className="relative group">
              {/* Outer HUD ring effect for input */}
              <div className="absolute -inset-1 bg-gradient-to-r from-hud-teal/20 via-hud-green/20 to-hud-teal/20 rounded-full blur opacity-50 group-hover:opacity-75 transition duration-500" />
              
              <div className="relative bg-black border border-white/20 rounded-full flex items-center p-2 shadow-2xl">
                <button type="button" onClick={onOpenVoice} className="w-10 h-10 rounded-full flex items-center justify-center text-slate-400 hover:text-hud-teal hover:bg-white/5 transition-colors">
                  <Mic className="w-5 h-5" />
                </button>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Initiate command sequence..."
                  className="flex-1 bg-transparent border-none outline-none px-4 text-white placeholder-slate-500 font-mono text-sm"
                  disabled={isProcessing}
                  autoFocus
                />
                <button 
                  type="submit"
                  disabled={isProcessing || !input.trim()}
                  className="w-10 h-10 rounded-full bg-hud-card border border-white/10 flex items-center justify-center text-white hover:border-hud-teal hover:text-hud-teal transition-all disabled:opacity-50"
                >
                  <Send className="w-4 h-4 ml-0.5" />
                </button>
              </div>
            </form>
          </div>

        </div>

        {/* Right Column: Projects & Status */}
        <div className="hidden lg:flex flex-col col-span-3 gap-4">
          
          {/* Card 4: Projects Timeline */}
          <div className="bg-hud-card rounded-3xl p-5 border border-white/5 h-72 min-h-[280px] overflow-hidden shadow-xl flex flex-col">
            <div className="flex justify-between items-center text-xs font-bold text-white uppercase tracking-wider mb-4">
              <span>Upcoming Milestones</span>
              <span className="text-slate-500">...</span>
            </div>
            
            <div className="flex-1 min-h-0">
              <D3Timeline />
            </div>
          </div>

          {/* Card 5: Product Stats / Bars */}
          <div className="bg-hud-card rounded-3xl p-5 border border-white/5 h-64 shadow-xl flex flex-col">
            <div className="flex justify-between items-center text-xs font-bold text-white uppercase tracking-wider mb-6">
              <span>Task Volatility</span>
              <span className="text-slate-500">...</span>
            </div>
            
            <div className="flex-1 flex items-end justify-between px-2 gap-2">
              {volatilityBars.map((bar, i) => (
                <div key={i} className="relative flex flex-col items-center w-6 gap-1 group">
                  <div className={`w-full rounded-full transition-all duration-500 ${bar.isGreen ? 'bg-hud-green/20 group-hover:bg-hud-green' : 'bg-hud-orange/20 group-hover:bg-hud-orange'}`} style={{ height: `${bar.h1}%` }}>
                     <div className="w-full h-full flex items-end pb-2 justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                       <span className="text-[9px] font-bold text-black">{bar.h1}</span>
                     </div>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${bar.isGreen ? 'bg-hud-green' : 'bg-hud-orange'}`} />
                  <div className={`w-full rounded-full transition-all duration-500 ${bar.isGreen ? 'bg-hud-green' : 'bg-hud-orange'}`} style={{ height: `${bar.h2}%` }} />
                </div>
              ))}
            </div>
            
            <div className="mt-4 pt-4 border-t border-white/5 flex justify-between text-[10px] uppercase font-mono text-slate-500">
              <div className="flex gap-4">
                <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full border border-hud-green" /> VALID</span>
                <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full border border-hud-orange" /> INVALID</span>
              </div>
              <span className="text-white font-bold">TOTAL: 1,012</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
