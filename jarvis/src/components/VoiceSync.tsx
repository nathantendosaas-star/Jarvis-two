import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  MicOff,
  X,
  Volume2,
  VolumeX,
  Sparkles,
  Zap,
  Activity
} from "lucide-react";

interface VoiceSyncProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscriptionResult: (text: string) => void;
  triggerNotification: (title: string, msg: string, type: any) => void;
  onMicActiveChange?: (active: boolean, stream?: MediaStream) => void;
}

export default function VoiceSync({
  isOpen,
  onClose,
  onTranscriptionResult,
  triggerNotification,
  onMicActiveChange,
}: VoiceSyncProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [transcribing, setTranscribing] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isOpen && !isRecording) {
      startAudioStream();
    }
    return () => {
      stopAudioStream();
    };
  }, [isOpen]);

  useEffect(() => {
    if (isRecording) {
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  const startAudioStream = async () => {
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
        setTranscribing(true);
        triggerNotification("Transcribing Waveform", "Sending audio package to gemini-3.1-flash-lite transcription engine...", "info");

        // Base64 process
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Data = reader.result?.toString().split(",")[1];
          if (!base64Data) {
            setTranscribing(false);
            triggerNotification("Sync Fail", "Empty base64 buffer", "error");
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
              onTranscriptionResult(data.text);
              triggerNotification("Vocal Sync Complete", `Transcribed: "${data.text.slice(0, 40)}..."`, "success");
              onClose();
            } else {
              triggerNotification("Silent Input", "No vocals detected in waveform.", "warning");
            }
          } catch (err) {
            console.error(err);
            triggerNotification("Sync Error", "Speech-to-text API did not respond.", "error");
          } finally {
            setTranscribing(false);
          }
        };

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      onMicActiveChange?.(true, stream);
      triggerNotification("Speech Core Ready", "Speak your prompt or operation objectives...", "info");
    } catch (err) {
      console.error(err);
      triggerNotification("Permissions Required", "Verify microphone peripheral permissions in system setting panels.", "error");
      onClose();
    }
  };

  const stopAudioStream = () => {
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 flex items-center justify-center animate-fade-in">
      
      {/* Container Card */}
      <div className="w-full max-w-sm bg-slate-950 border border-slate-800 rounded-3xl p-6 relative overflow-hidden shadow-2xl flex flex-col items-center justify-between min-h-[380px]">
        
        {/* Glow backdrop circles */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -z-10" />

        {/* Closer button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 hover:bg-slate-900 rounded-lg text-slate-500 hover:text-white cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Category Header */}
        <div className="text-center">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">COGNITIVE_SYNTAX_MIC /</span>
          <h2 className="text-sm font-display font-semibold text-white tracking-wide mt-1">Vocal Synchronizer</h2>
        </div>

        {/* Interfacing Glowing Orb Visualizer */}
        <div className="py-6 flex items-center justify-center relative">
          {/* Iron Man arc reactor styled pulse waves */}
          <div className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-500 ${
            transcribing ? "bg-purple-600/10 border-2 border-purple-500/40" :
            isRecording ? "voice-pulse-active bg-blue-500/20 border-2 border-blue-500/60" :
            "bg-slate-900 border border-slate-800"
          }`}>
            {transcribing ? (
              <Activity className="w-8 h-8 text-purple-400 animate-spin" />
            ) : isRecording ? (
              <Mic className="w-8 h-8 text-blue-400" />
            ) : (
              <MicOff className="w-8 h-8 text-slate-600" />
            )}
          </div>

          {/* Orbit rotating rings */}
          {isRecording && (
            <div className="absolute inset-0 border border-blue-500/10 rounded-full animate-ping scale-110" />
          )}
        </div>

        {/* Operating text */}
        <div className="text-center space-y-1">
          {transcribing ? (
            <span className="text-xs font-mono text-purple-400 font-bold animate-pulse uppercase">TRANSCRIBING_COGNITIVE_WAVEFORM...</span>
          ) : isRecording ? (
            <>
              <span className="text-xs text-slate-300 font-medium block">Voice capture pipeline online</span>
              <span className="text-[11px] font-mono text-slate-500">Duration: {formatTime(recordingTime)}</span>
            </>
          ) : (
            <span className="text-xs text-slate-500">Synchronizer standing by</span>
          )}
        </div>

        {/* Action Button */}
        <button
          onClick={isRecording ? stopAudioStream : startAudioStream}
          disabled={transcribing}
          className={`w-full py-2.5 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-2 cursor-pointer ${
            isRecording
              ? "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/15"
              : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/15"
          }`}
        >
          {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          <span>{isRecording ? "Stop Vocal Sync" : "Initiate Vocal Sync"}</span>
        </button>

      </div>

    </div>
  );
}
