import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  Mic,
  MicOff,
  Globe,
  Trash2,
  Paperclip,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  Pin,
  Bookmark,
  ChevronRight,
  ExternalLink,
  Bot,
  Play,
  Wrench
} from "lucide-react";
import { ChatMessage, SystemNotification } from "../types";
import { audioService } from "../utils/audioService";

interface ChatViewProps {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  selectedModel: string;
  triggerNotification: (title: string, msg: string, type: any) => void;
  systemInstruction?: string;
  pendingVoicePrompt?: string | null;
  clearPendingVoicePrompt?: () => void;
  onMicActiveChange?: (active: boolean, stream?: MediaStream) => void;
}

function renderInlineMarkdown(text: string) {
  const parts = text.split("**");
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return (
        <strong key={index} className="font-bold text-white">
          {part}
        </strong>
      );
    }
    return part;
  });
}

function renderMarkdown(content: string) {
  const lines = content.split("\n");
  return lines.map((line, idx) => {
    const headerMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      let text = headerMatch[2];
      text = text.replace(/\*\*/g, ""); // Strip raw bold asterisks from inside headers
      const className =
        level === 1
          ? "text-lg font-bold text-white mt-4 mb-2 block"
          : level === 2
          ? "text-base font-bold text-white mt-3 mb-2 block"
          : "text-xs font-bold text-purple-350 mt-2 mb-1 block";
      return (
        <span key={idx} className={className}>
          {text}
        </span>
      );
    }

    const bulletMatch = line.match(/^(\*\s+|\-\s+|\u2022\s+)(.*)$/);
    if (bulletMatch) {
      const text = bulletMatch[2];
      return (
        <span key={idx} className="flex items-start gap-2 pl-3 my-1 leading-relaxed text-slate-300">
          <span className="text-purple-400 mt-1 shrink-0 select-none text-[8px]">•</span>
          <span>{renderInlineMarkdown(text)}</span>
        </span>
      );
    }

    if (line.trim() === "") {
      return <span key={idx} className="block h-2" />;
    }

    return (
      <span key={idx} className="block leading-relaxed my-0.5">
        {renderInlineMarkdown(line)}
      </span>
    );
  });
}

export default function ChatView({
  messages,
  setMessages,
  selectedModel,
  triggerNotification,
  systemInstruction,
  pendingVoicePrompt,
  clearPendingVoicePrompt,
  onMicActiveChange,
}: ChatViewProps) {
  const [inputText, setInputText] = useState("");
  const [useSearch, setUseSearch] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showPinned, setShowPinned] = useState(false);

  // Voice recording state
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Pinned messages state
  const [pinnedMsgIds, setPinnedMsgIds] = useState<string[]>([]);
  const [bookmarkedMsgIds, setBookmarkedMsgIds] = useState<string[]>([]);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  // Handle voice recording timer
  useEffect(() => {
    if (isRecording) {
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    }
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    };
  }, [isRecording]);

  // Audio recording function
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        triggerNotification("Syncing Audio", "Transcribing recording via Gemini flash-core...", "info");

        // Convert audio blob to base64
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Data = reader.result?.toString().split(",")[1];
          if (!base64Data) {
            triggerNotification("Sync Failed", "Could not process audio waveform.", "error");
            return;
          }

          try {
            const res = await fetch("/api/transcribe", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ audioData: base64Data, mimeType: "audio/webm" })
            });

            const data = await res.json();
            if (data.text && data.text.trim()) {
              triggerNotification("Sync Complete", "Voice input submitted directly.", "success");
              void sendMessage(data.text);
            } else {
              triggerNotification("Silent Input", "No voice transcription detected.", "warning");
            }
          } catch (err: any) {
            console.error("Transcription service offline:", err);
            triggerNotification("Transcription Fail", "Audio service did not respond.", "error");
          }
        };

        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      onMicActiveChange?.(true, stream);
      triggerNotification("Vocal Sync Mode", "Listening to microphone input...", "info");
    } catch (err: any) {
      console.error("Microphone access blocked:", err);
      triggerNotification("Permissions Required", "Microphone access is blocked in this container frame context.", "error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      onMicActiveChange?.(false);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  // Auto-submit voice prompt if forwarded from global listener
  useEffect(() => {
    if (pendingVoicePrompt && clearPendingVoicePrompt) {
      const text = pendingVoicePrompt;
      clearPendingVoicePrompt();
      void sendMessage(text);
    }
  }, [pendingVoicePrompt, clearPendingVoicePrompt]);

  const sendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || isStreaming) return;

    // Cancel any previous speech
    audioService.cancelSpeech();

    const userMessage: ChatMessage = {
      id: "msg-" + Date.now(),
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);

    // Create modeling stream message placeholder
    const assistantMessageId = "msg-" + (Date.now() + 1);
    const assistantMessagePlaceholder: ChatMessage = {
      id: assistantMessageId,
      role: "model",
      content: "",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      model: selectedModel,
      useSearch,
      isThinking: true
    };

    setMessages(prev => [...prev, assistantMessagePlaceholder]);

    try {
      const historyPayload = messages.map(m => ({
        role: m.role,
        content: m.content
      }));

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: textToSend,
          history: historyPayload,
          systemInstruction,
          useSearch,
          model: selectedModel
        })
      });

      if (!response.ok) {
        throw new Error("Cognitive link down");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) throw new Error("Could not initialize SSE decoder");

      let accumulatedText = "";
      let lastSpokenIndex = 0;
      let lastCitations: any[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();
            if (dataStr === "[DONE]") {
              // Complete streaming
              break;
            }

              try {
                const dataObj = JSON.parse(dataStr);

                // ── Tool-call event ──────────────────────────────────────────
                if (dataObj.workspaceChanged) {
                window.dispatchEvent(new CustomEvent("jarvis:workspace-changed", { detail: dataObj.workspaceChanged }));
                continue;
              }

              if (dataObj.notification) {
                window.dispatchEvent(new CustomEvent("jarvis:notification", { detail: dataObj.notification }));
                continue;
              }

              if (dataObj.toolCall) {
                  const tc = dataObj.toolCall;
                  setMessages(prev =>
                    prev.map(m => {
                      if (m.id === assistantMessageId) {
                        return {
                          ...m,
                          isThinking: tc.status === "running",
                          toolCall: {
                            name: tc.name,
                            args: tc.args || {},
                            status: tc.status,
                          },
                        };
                      }
                      return m;
                    })
                  );
                  continue;
                }

                // ── Normal text / error chunks ───────────────────────────────
                if (dataObj.error) {
                  accumulatedText = `❌ Core error: ${dataObj.error}\n\nMake sure your GEMINI_API_KEY is configured in Settings > Secrets.`;
                } else {
                  accumulatedText += dataObj.text || "";
                  if (dataObj.searchChunks && dataObj.searchChunks.length > 0) {
                    lastCitations = dataObj.searchChunks;
                  }

                  if (dataObj.text) {
                    // Play subtle sci-fi typing click
                    audioService.playTypingSound();

                    // Speech synthesis sentence-by-sentence parsing
                    const newText = accumulatedText.slice(lastSpokenIndex);
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
                }

                // Update the latest assistant message
                setMessages(prev =>
                  prev.map(m => {
                    if (m.id === assistantMessageId) {
                      return {
                        ...m,
                        content: accumulatedText,
                        isThinking: false,
                        // Clear toolCall once real text starts arriving
                        toolCall: accumulatedText ? undefined : m.toolCall,
                        webCitations: lastCitations.map(c => ({
                          uri: c.web?.uri || "",
                          title: c.web?.title || "Search Grounding Link"
                        }))
                      };
                    }
                    return m;
                  })
                );
              } catch (err) {
                // Line may have been cut or is not JSON
              }
          }
        }
      }

      // Speak any remaining response that wasn't punctuated
      const remainingText = accumulatedText.slice(lastSpokenIndex).trim();
      if (remainingText) {
        audioService.speak(remainingText);
      }
    } catch (error: any) {
      console.error("Streaming error:", error);
      setMessages(prev =>
        prev.map(m => {
          if (m.id === assistantMessageId) {
            return {
              ...m,
              content: `⚠️ Failed to establish live channel.\n\nVerify your local configurations. Error details: ${error.message}`,
              isThinking: false
            };
          }
          return m;
        })
      );
      triggerNotification("Engine Sync Fault", "Vocal sync pipeline failed.", "error");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    const text = inputText;
    setInputText("");
    void sendMessage(text);
  };

  const handleClearHistory = () => {
    setMessages([]);
    triggerNotification("Engine Cleaned", "Active chat timeline wiped.", "info");
  };

  const togglePin = (id: string) => {
    setPinnedMsgIds(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
    triggerNotification("Workspace Sync", "Message priority state updated.", "success");
  };

  const toggleBookmark = (id: string) => {
    setBookmarkedMsgIds(prev =>
      prev.includes(id) ? prev.filter(b => b !== id) : [...prev, id]
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden text-slate-200">
      
      {/* Search Grounding Bar indicator */}
      <div className="px-6 py-2.5 bg-slate-950/40 border-b border-slate-800/40 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-purple-400" />
          <span className="text-slate-400">COGNITIVE_PIPELINE:</span>
          <span className="text-purple-400 font-bold">{selectedModel}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setUseSearch(!useSearch);
              triggerNotification(
                "Grounding Switch",
                `Google Search Grounding ${!useSearch ? "ENABLED" : "DISABLED"} for the active thread.`,
                "info"
              );
            }}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border transition-all cursor-pointer ${
              useSearch
                ? "bg-blue-500/10 border-blue-500/50 text-blue-400 font-bold"
                : "bg-transparent border-slate-800 text-slate-500 hover:text-slate-400"
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Search Grounding</span>
          </button>
          <button
            onClick={handleClearHistory}
            className="p-1 hover:bg-slate-800 text-slate-500 hover:text-red-400 rounded transition-colors cursor-pointer"
            title="Wipe Thread History"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Messages timeline */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-center text-xs text-slate-500">
            No chat messages recorded yet.
          </div>
        )}
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          const isPinned = pinnedMsgIds.includes(msg.id);
          const isBookmarked = bookmarkedMsgIds.includes(msg.id);

          return (
            <div
              key={msg.id}
              className={`flex flex-col max-w-3xl ${isUser ? "ml-auto items-end" : "mr-auto items-start"} w-full group animate-fade-in`}
            >
              {/* Message Header (Sender name, tags) */}
              <div className="flex items-center gap-2 mb-1 text-[10px] font-mono text-slate-500">
                <span>{isUser ? "USER" : "JARVIS_OS"}</span>
                <span>•</span>
                <span>{msg.timestamp}</span>
                {msg.model && <span className="bg-slate-900 border border-slate-800 px-1.5 py-0.2 rounded text-[9px] text-slate-400">{msg.model}</span>}
              </div>

              {/* Message Body Bubble */}
              <div
                className={`p-4 rounded-2xl text-xs leading-relaxed border ${
                  isUser
                    ? "bg-blue-600/10 border-blue-500/20 text-blue-100 rounded-tr-none"
                    : "bg-slate-900/40 border-slate-800/40 text-slate-200 rounded-tl-none"
                } relative`}
              >
                {/* Thinking / Tool-execution state */}
                {msg.isThinking ? (
                  msg.toolCall ? (
                    <div className="flex items-center gap-2 py-1 text-[11px] font-mono">
                      <Wrench className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                      <span className="text-amber-400">Executing tool:</span>
                      <span className="text-amber-300 font-bold">{msg.toolCall.name}</span>
                      <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-ping" />
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 py-1">
                      <span className="w-2 h-2 bg-blue-500 rounded-full typing-dot" />
                      <span className="w-2 h-2 bg-blue-500 rounded-full typing-dot" />
                      <span className="w-2 h-2 bg-blue-500 rounded-full typing-dot" />
                    </div>
                  )
                ) : (
                  <>
                    {/* Completed tool call badge */}
                    {msg.toolCall && msg.toolCall.status === "completed" && (
                      <div className="flex items-center gap-1.5 mb-2 text-[10px] font-mono text-emerald-400 bg-emerald-500/5 border border-emerald-500/15 rounded-lg px-2.5 py-1">
                        <Wrench className="w-3 h-3" />
                        <span>Tool executed:</span>
                        <span className="font-bold">{msg.toolCall.name}</span>
                        <CheckCircle2 className="w-3 h-3 ml-auto" />
                      </div>
                    )}
                    <div className="whitespace-pre-wrap font-sans break-words selection:bg-blue-500/30">
                      {renderMarkdown(msg.content)}
                    </div>
                  </>
                )}

                {/* Google Search Citations panel */}
                {!isUser && msg.webCitations && msg.webCitations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/60 text-[10px] space-y-1">
                    <span className="font-mono text-slate-500 font-bold tracking-wider uppercase">Grounding Citations:</span>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {msg.webCitations.map((c, idx) => (
                        <a
                          key={idx}
                          href={c.uri}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 bg-blue-500/5 hover:bg-blue-500/10 border border-blue-500/10 hover:border-blue-500/20 px-2 py-0.5 rounded text-blue-400 transition-colors"
                        >
                          <Globe className="w-3 h-3 shrink-0" />
                          <span className="truncate max-w-xs">{c.title || c.uri}</span>
                          <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action buttons on message hover */}
                <div className="absolute top-2 -right-8 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-1">
                  <button
                    onClick={() => togglePin(msg.id)}
                    className={`p-1 rounded bg-slate-950 border border-slate-800 text-slate-500 hover:text-white cursor-pointer ${
                      isPinned ? "text-amber-400" : ""
                    }`}
                  >
                    <Pin className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => toggleBookmark(msg.id)}
                    className={`p-1 rounded bg-slate-950 border border-slate-800 text-slate-500 hover:text-white cursor-pointer ${
                      isBookmarked ? "text-blue-400" : ""
                    }`}
                  >
                    <Bookmark className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
        <div ref={chatEndRef} />
      </div>

      {/* Unified Input bar & Voice feedback */}
      <div className="p-4 bg-slate-950/20 border-t border-slate-800/40">
        
        {/* If user is voice recording */}
        {isRecording && (
          <div className="mb-3 px-4 py-3 bg-blue-500/10 border border-blue-500/30 rounded-xl flex items-center justify-between animate-pulse">
            <div className="flex items-center gap-3 text-xs">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              <span className="font-mono text-blue-400 font-bold">VOCAL ENCODER ACTIVE</span>
              <span className="text-slate-400">({formatTime(recordingTime)})</span>
            </div>
            <button
              onClick={stopRecording}
              className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg text-[10px] tracking-wide transition-all uppercase cursor-pointer"
            >
              Interrupt Stream
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            placeholder={isRecording ? "Listening..." : "Message JARVIS or instruct action..."}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isStreaming || isRecording}
            className="w-full glass-input pl-11 pr-24 py-3 text-xs h-12 focus:ring-1 focus:ring-blue-500/50"
          />

          {/* Attachment action */}
          <button
            type="button"
            className="absolute left-3 p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-slate-300 cursor-pointer"
            onClick={() => triggerNotification("Attachment Unavailable", "No real attachment upload flow is connected here yet.", "warning")}
          >
            <Paperclip className="w-4 h-4" />
          </button>

          {/* Right Action buttons */}
          <div className="absolute right-3 flex items-center gap-1.5">
            {/* Mic recording sync */}
            {isRecording ? (
              <button
                type="button"
                onClick={stopRecording}
                className="p-2 bg-red-500 hover:bg-red-600 rounded-lg text-white transition-all cursor-pointer shadow-md shadow-red-500/20"
              >
                <MicOff className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={startRecording}
                disabled={isStreaming}
                className="p-2 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-blue-400 transition-colors cursor-pointer"
              >
                <Mic className="w-4 h-4" />
              </button>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={isStreaming || isRecording || !inputText.trim()}
              className="p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 rounded-lg text-white transition-all cursor-pointer shadow-md shadow-blue-600/10"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>

        <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <div className="flex items-center gap-1.5">
            <span>Grounding Core: {useSearch ? "Active" : "Disabled"}</span>
            <span>•</span>
            <span>Synthesizer Model: {selectedModel}</span>
          </div>
          <span>Shift + Enter for new line</span>
        </div>

      </div>

    </div>
  );
}
