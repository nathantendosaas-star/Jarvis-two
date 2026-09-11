/**
 * start-dev.js — Unified JARVIS development runner.
 * Boots both the Python FastAPI backend and the Vite React frontend concurrently.
 * Usage: node start-dev.js  (mapped to `npm run dev`)
 */
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import net from "net";

const isWin = process.platform === "win32";
const cwd = process.cwd();

// 1. Detect local virtual environment Python executable
let pythonCmd = isWin ? "python" : "python3";
const venvPath = isWin
  ? path.join(cwd, ".venv", "Scripts", "python.exe")
  : path.join(cwd, ".venv", "bin", "python");
const viteEntry = path.join(cwd, "node_modules", "vite", "bin", "vite.js");

if (fs.existsSync(venvPath)) {
  console.log(`\x1b[32m✔ Local virtual environment (.venv) detected at ${venvPath}\x1b[0m`);
  pythonCmd = venvPath;
} else {
  console.log(`\x1b[33m⚠ No virtual environment detected. Falling back to global "${pythonCmd}" command.\x1b[0m`);
}

console.log("\x1b[36m%s\x1b[0m", "🚀 Starting JARVIS AI OS...");
console.log("\x1b[33m%s\x1b[0m", "   Backend:  http://127.0.0.1:8000");
console.log("\x1b[33m%s\x1b[0m", "   Frontend: http://localhost:3000");

// 2. Spawn FastAPI backend on port 8000
const backend = spawn(
  pythonCmd,
  [
    "-m",
    "uvicorn",
    "backend.src.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--reload",
    "--reload-dir",
    "backend",
  ],
  { stdio: "inherit", shell: false, cwd }
);

// 3. Spawn Vite dev server on port 3000 after backend is ready
const frontendCmd = fs.existsSync(viteEntry) ? process.execPath : "npx";
const frontendArgs = [
  ...(fs.existsSync(viteEntry) ? [viteEntry] : ["vite"]),
  "--host",
  "localhost",
  "--port",
  "3000",
  "--strictPort",
];

let frontend;

function startFrontend() {
  frontend = spawn(frontendCmd, frontendArgs, {
    stdio: "inherit",
    shell: false,
    cwd,
  });

  frontend.on("exit", (code) => {
    if (code !== 0 && code !== null) console.error(`Frontend exited with code ${code}`);
  });
}

function cleanup() {
  backend.kill();
  if (frontend) frontend.kill();
  process.exit();
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

backend.on("exit", (code) => {
  if (code !== 0 && code !== null) console.error(`Backend exited with code ${code}`);
});

console.log("\x1b[90m%s\x1b[0m", "⌛ Waiting for backend (127.0.0.1:8000) to be ready...");

function checkBackendReady(port, host, callback) {
  const socket = new net.Socket();
  const tryConnect = () => {
    socket.connect(port, host);
  };

  socket.on("connect", () => {
    socket.destroy();
    callback();
  });

  socket.on("error", () => {
    setTimeout(tryConnect, 200);
  });

  tryConnect();
}

checkBackendReady(8000, "127.0.0.1", () => {
  console.log("\x1b[32m✔ Backend is ready! Booting Frontend...\x1b[0m");
  startFrontend();
});
