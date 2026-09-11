import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

// Enable JSON parse with a larger limit for audio uploads
app.use(express.json({ limit: "50mb" }));

// Lazy initializer for Google GenAI client to avoid crash on startup if key is missing
let aiClient: GoogleGenAI | null = null;
function getAI(): GoogleGenAI {
  if (!aiClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY environment variable is required. Configure it in Settings > Secrets.");
    }
    aiClient = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// Check if Gemini API key is configured
app.get("/api/config", (req, res) => {
  res.json({
    hasApiKey: !!process.env.GEMINI_API_KEY,
    appUrl: process.env.APP_URL || "http://localhost:3000"
  });
});

// Helper function to call generateContent with retry and fallback
async function generateContentWithRetryAndFallback(
  ai: GoogleGenAI,
  params: Parameters<typeof ai.models.generateContent>[0]
): Promise<ReturnType<typeof ai.models.generateContent>> {
  const maxRetries = 2;
  let attempt = 0;
  const originalModel = params.model;

  while (true) {
    try {
      return await ai.models.generateContent(params);
    } catch (error: any) {
      attempt++;
      console.warn(`Gemini API attempt ${attempt} failed for model ${params.model}:`, error.message || error);

      const isTransient =
        error.status === 503 ||
        error.status === 429 ||
        String(error).includes("503") ||
        String(error).includes("429") ||
        String(error).includes("UNAVAILABLE") ||
        String(error).includes("high demand") ||
        String(error).includes("ResourceExhausted") ||
        String(error).includes("overloaded");

      // Fallback transitions
      if (params.model === "gemini-3.1-flash-lite") {
        console.log("Switching to fallback model: gemini-3.5-flash due to primary model error.");
        params.model = "gemini-3.5-flash";
        attempt = 0;
        continue;
      }
      if (isTransient && attempt <= maxRetries) {
        console.log(`Transient error encountered. Retrying in ${attempt}s...`);
        await new Promise((resolve) => setTimeout(resolve, 1000 * attempt));
        continue;
      }

      throw error;
    }
  }
}

// Helper function to call generateContentStream with retry and fallback
async function generateContentStreamWithRetryAndFallback(
  ai: GoogleGenAI,
  params: Parameters<typeof ai.models.generateContentStream>[0]
): Promise<ReturnType<typeof ai.models.generateContentStream>> {
  const maxRetries = 2;
  let attempt = 0;
  const originalModel = params.model;

  while (true) {
    try {
      return await ai.models.generateContentStream(params);
    } catch (error: any) {
      attempt++;
      console.warn(`Gemini API stream attempt ${attempt} failed for model ${params.model}:`, error.message || error);

      const isTransient =
        error.status === 503 ||
        error.status === 429 ||
        String(error).includes("503") ||
        String(error).includes("429") ||
        String(error).includes("UNAVAILABLE") ||
        String(error).includes("high demand") ||
        String(error).includes("ResourceExhausted") ||
        String(error).includes("overloaded");

      // Fallback transitions
      if (params.model === "gemini-3.1-flash-lite") {
        console.log("Switching stream to fallback model: gemini-3.5-flash due to primary model error.");
        params.model = "gemini-3.5-flash";
        attempt = 0;
        continue;
      }
      if (isTransient && attempt <= maxRetries) {
        console.log(`Transient error encountered on stream. Retrying in ${attempt}s...`);
        await new Promise((resolve) => setTimeout(resolve, 1000 * attempt));
        continue;
      }

      throw error;
    }
  }
}

// Chat stream API route
app.post("/api/chat", async (req, res) => {
  try {
    const { message, history = [], systemInstruction, useSearch = false, model = "gemini-3.1-flash-lite" } = req.body;

    if (!message) {
      res.status(400).json({ error: "Message is required" });
      return;
    }

    const ai = getAI();

    // Map model selection
    // Allowed models: 'gemini-3.1-flash-lite' for fast, 'gemini-3.5-flash' for general
    let selectedModel = "gemini-3.1-flash-lite";
    if (model === "gemini-3.5-flash") {
      selectedModel = "gemini-3.5-flash";
    }

    // Prepare contents payload
    const contents = [
      ...history.map((msg: any) => ({
        role: msg.role === "user" ? "user" : "model",
        parts: [{ text: msg.content || msg.text || "" }]
      })),
      { role: "user", parts: [{ text: message }] }
    ];

    // Set headers for streaming Server-Sent Events (SSE)
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");

    const tools = useSearch ? [{ googleSearch: {} }] : undefined;

    const stream = await generateContentStreamWithRetryAndFallback(ai, {
      model: selectedModel,
      contents,
      config: {
        systemInstruction: systemInstruction || "You are JARVIS, an advanced AI Operating System. Answer elegantly, with a technical, refined, and helpful persona.",
        tools,
      },
    });

    let groundingChunks: any[] = [];

    for await (const chunk of stream) {
      const text = chunk.text || "";
      const searchChunks = chunk.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
      if (searchChunks.length > 0) {
        groundingChunks = searchChunks;
      }
      res.write(`data: ${JSON.stringify({ text, searchChunks: groundingChunks })}\n\n`);
    }

    res.write("data: [DONE]\n\n");
    res.end();
  } catch (error: any) {
    console.error("Error in /api/chat:", error);
    res.write(`data: ${JSON.stringify({ error: error.message || "An unexpected error occurred." })}\n\n`);
    res.end();
  }
});

// Transcribe audio using gemini-3.1-flash-lite
app.post("/api/transcribe", async (req, res) => {
  try {
    const { audioData, mimeType } = req.body;
    if (!audioData) {
      res.status(400).json({ error: "audioData (base64) is required" });
      return;
    }

    const ai = getAI();

    const response = await generateContentWithRetryAndFallback(ai, {
      model: "gemini-3.1-flash-lite",
      contents: [
        {
          inlineData: {
            mimeType: mimeType || "audio/webm",
            data: audioData,
          },
        },
        { text: "Accurately transcribe this audio recording. Do not explain, add comments, or say anything else - output ONLY the precise transcribed words. If the audio is silent or unreadable, return empty text." },
      ],
    });

    res.json({ text: response.text || "" });
  } catch (error: any) {
    console.error("Transcription error:", error);
    res.status(500).json({ error: error.message || "Failed to transcribe audio." });
  }
});

// Set up Vite or Static files depending on mode
async function bootstrap() {
  if (process.env.NODE_ENV !== "production") {
    console.log("Starting server in DEVELOPMENT mode with Vite Middleware...");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    console.log("Starting server in PRODUCTION mode with static files serving...");
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`JARVIS OS active and listening on port ${PORT}`);
  });
}

bootstrap();
