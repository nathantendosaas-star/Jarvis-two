// Web Speech Synthesis (Talk-Back Engine) and Web Audio API Sci-Fi Sound Effects Service

class AudioService {
  private ttsEnabled: boolean = true;
  private sfxEnabled: boolean = true;
  private ttsQueue: string[] = [];
  private isSpeaking: boolean = false;
  private activeUtterance: SpeechSynthesisUtterance | null = null;
  private currentSpeakTimer: NodeJS.Timeout | null = null;

  // Web Audio Context for Sound Effects
  private audioCtx: AudioContext | null = null;

  constructor() {
    // Read initial settings from localStorage
    this.ttsEnabled = localStorage.getItem("jarvis-tts-enabled") !== "false";
    this.sfxEnabled = localStorage.getItem("jarvis-sfx-enabled") !== "false";

    // Setup voices changed listener
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = () => {
        // Warm up voices load
        window.speechSynthesis.getVoices();
      };
    }
  }

  // --- Mute / Unmute Controls ---
  public getTtsEnabled(): boolean {
    return this.ttsEnabled;
  }

  public setTtsEnabled(enabled: boolean) {
    this.ttsEnabled = enabled;
    localStorage.setItem("jarvis-tts-enabled", String(enabled));
    if (!enabled) {
      this.cancelSpeech();
    }
  }

  public getSfxEnabled(): boolean {
    return this.sfxEnabled;
  }

  public setSfxEnabled(enabled: boolean) {
    this.sfxEnabled = enabled;
    localStorage.setItem("jarvis-sfx-enabled", String(enabled));
  }

  // --- Web Audio API Synth Sci-Fi Sound Effects ---
  private initAudioContext() {
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtx = new AudioContextClass();
    }
    if (this.audioCtx.state === "suspended") {
      void this.audioCtx.resume();
    }
  }

  // Soft digital boot chime/sweep
  public playBootSound() {
    if (!this.sfxEnabled) return;
    try {
      this.initAudioContext();
      const ctx = this.audioCtx!;
      const now = ctx.currentTime;

      // Layer 1: Low ambient hum
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(110, now);
      osc1.frequency.exponentialRampToValueAtTime(440, now + 1.2);
      gain1.gain.setValueAtTime(0.001, now);
      gain1.gain.linearRampToValueAtTime(0.15, now + 0.3);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 1.5);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      // Layer 2: Higher digital chime sweep
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = "triangle";
      osc2.frequency.setValueAtTime(440, now);
      osc2.frequency.setValueAtTime(880, now + 0.15);
      osc2.frequency.setValueAtTime(1320, now + 0.3);
      osc2.frequency.exponentialRampToValueAtTime(1760, now + 0.6);
      gain2.gain.setValueAtTime(0.001, now);
      gain2.gain.linearRampToValueAtTime(0.1, now + 0.2);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 1.2);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 1.5);
      osc2.stop(now + 1.5);
    } catch (e) {
      console.warn("Could not play boot sound", e);
    }
  }

  // Soft digital chirp when opening the mic
  public playMicOpenSound() {
    if (!this.sfxEnabled) return;
    try {
      this.initAudioContext();
      const ctx = this.audioCtx!;
      const now = ctx.currentTime;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      // Pleasant upward chirp: 880Hz -> 1320Hz in 120ms
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.exponentialRampToValueAtTime(1320, now + 0.12);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.08, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.16);
    } catch (e) {
      console.warn("Could not play mic open sound", e);
    }
  }

  // Soft digital finished chirp when vocal sync finishes
  public playMicCloseSound() {
    if (!this.sfxEnabled) return;
    try {
      this.initAudioContext();
      const ctx = this.audioCtx!;
      const now = ctx.currentTime;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      // Pleasant downward/finished chirp: 1100Hz -> 660Hz in 150ms
      osc.frequency.setValueAtTime(1100, now);
      osc.frequency.exponentialRampToValueAtTime(660, now + 0.15);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.08, now + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.19);
    } catch (e) {
      console.warn("Could not play mic close sound", e);
    }
  }

  // Crisp digital "typing/thinking" clicks
  public playTypingSound() {
    if (!this.sfxEnabled) return;
    try {
      this.initAudioContext();
      const ctx = this.audioCtx!;
      const now = ctx.currentTime;

      // Ultra-short high-pass filtered noise/sine click
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(1800 + Math.random() * 400, now);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.015, now + 0.002);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.015);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.02);
    } catch (e) {
      // Ignore audio glitches during heavy rendering
    }
  }

  // --- Text-To-Speech (Talk-Back Engine) ---
  public speak(text: string) {
    if (!this.ttsEnabled) return;

    // Clean string from basic markdown syntax
    const cleanedText = text
      .replace(/[*_#`~[\]()]/g, "") // remove stars, hashes, code ticks, etc.
      .trim();

    if (!cleanedText) return;

    this.ttsQueue.push(cleanedText);
    this.processQueue();
  }

  private processQueue() {
    if (this.isSpeaking || this.ttsQueue.length === 0) return;

    const textToSpeak = this.ttsQueue.shift();
    if (!textToSpeak) return;

    this.isSpeaking = true;

    try {
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      this.activeUtterance = utterance;

      const voices = window.speechSynthesis.getVoices();

      // Look for a British-sounding male voice: en-GB + male/George/Hazel/Oliver/etc.
      let voice = voices.find(v => v.lang.toLowerCase() === "en-gb" && v.name.toLowerCase().includes("male"));
      if (!voice) {
        voice = voices.find(v => v.lang.toLowerCase() === "en-gb" && v.name.toLowerCase().includes("george"));
      }
      if (!voice) {
        voice = voices.find(v => v.lang.toLowerCase().startsWith("en-gb"));
      }
      // Fallback: Google American English (Google US English) or any Google English
      if (!voice) {
        voice = voices.find(v => v.name.toLowerCase().includes("google us english"));
      }
      if (!voice) {
        voice = voices.find(v => v.name.toLowerCase().includes("google") && v.lang.toLowerCase().startsWith("en"));
      }
      // Ultimate fallbacks
      if (!voice) {
        voice = voices.find(v => v.lang.toLowerCase().startsWith("en"));
      }
      if (!voice && voices.length > 0) {
        voice = voices[0];
      }

      if (voice) {
        utterance.voice = voice;
      }

      // Elegant, professional, male feel configurations
      utterance.rate = 1.05; // Slightly faster for slick AI feel
      utterance.pitch = 0.95; // Slightly deeper/warm tone

      utterance.onend = () => {
        this.isSpeaking = false;
        this.activeUtterance = null;
        this.processQueue();
      };

      utterance.onerror = (e) => {
        console.warn("TTS Utterance error:", e);
        this.isSpeaking = false;
        this.activeUtterance = null;
        this.processQueue();
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("Speech Synthesis failed:", err);
      this.isSpeaking = false;
      this.activeUtterance = null;
    }
  }

  public cancelSpeech() {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    this.ttsQueue = [];
    this.isSpeaking = false;
    this.activeUtterance = null;
  }
}

export const audioService = new AudioService();
