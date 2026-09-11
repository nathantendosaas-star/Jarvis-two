import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from .tools import ToolRegistry

class AgentLoadError(Exception):
    pass

class AgentDef(BaseModel):
    name: str
    description: str
    tools: List[str] = []
    model: Literal["inherit", "flash", "pro"] = "inherit"
    mainAgent: bool = True
    subagent: bool = True
    commandExecutionPolicy: Literal["off", "auto", "eager", "sandbox"] = "sandbox"
    mcpServers: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    plugins: List[str] = Field(default_factory=list)
    system_prompt: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Agent name must consist of lower-case alphanumeric characters or dashes only.")
        return v

    @field_validator("commandExecutionPolicy", mode="before")
    @classmethod
    def validate_execution_policy(cls, v: Any) -> str:
        if isinstance(v, bool):
            return "sandbox" if v else "off"
        if isinstance(v, str):
            return v.lower()
        return v

def split_frontmatter(content: str) -> Tuple[dict, str]:
    """Splits markdown file content into frontmatter dict and prompt body."""
    content_stripped = content.strip()
    if content_stripped.startswith("---"):
        parts = content_stripped.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                return fm, body
            except Exception as e:
                raise AgentLoadError(f"YAML parsing failed in frontmatter: {e}")
    return {}, content_stripped

class AgentRegistry:
    def __init__(self, workspace_root: Optional[Path] = None, tool_registry: Optional[ToolRegistry] = None):
        self.workspace_root = workspace_root or Path.cwd().resolve()
        self.tool_registry = tool_registry or ToolRegistry()
        self.agents: Dict[str, AgentDef] = {}
        # Map agent name to (file_path, mtime)
        self._loaded_paths: Dict[str, Tuple[Path, float]] = {}

        # Sane standard definitions for built-in/seeded agents
        self._ensure_default_agents()
        self.load_all()

    def _ensure_default_agents(self):
        """Creates standard default agents on disk if directories are empty, to seed the workspace."""
        agents_dir = self.workspace_root / ".agents" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # 1. researcher.md
        researcher_path = agents_dir / "researcher.md"
        if not researcher_path.exists():
            researcher_path.write_text("""---
name: researcher
description: Specialized in deep workspace research, grep searching, and file audits.
tools:
  - view_file
  - grep_search
model: flash
mainAgent: true
subagent: true
commandExecutionPolicy: off
---
# System Prompt
You are a meticulous Research Subagent. Your primary purpose is to scan files, locate key patterns, and retrieve context for the orchestrator.
Do not modify or write any files. Keep your suggestions descriptive.
""", encoding="utf-8")

        # 2. coder.md
        coder_path = agents_dir / "coder.md"
        if not coder_path.exists():
            coder_path.write_text("""---
name: coder
description: Specialized in writing, modifying, and refactoring workspace files.
tools:
  - view_file
  - write_file
  - grep_search
model: pro
mainAgent: true
subagent: true
commandExecutionPolicy: sandbox
---
# System Prompt
You are an expert Software Engineer Subagent. You excel at reading source code and writing clean, robust, and commented code.
Always make sure to verify file contents before rewriting them.
""", encoding="utf-8")

        # 3. code-auditor.md
        auditor_path = agents_dir / "code-auditor.md"
        if not auditor_path.exists():
            auditor_path.write_text("""---
name: code-auditor
description: Specialized in security audits, static analysis, and command-line diagnostics.
tools:
  - view_file
  - grep_search
  - run_command
model: pro
mainAgent: false
subagent: true
commandExecutionPolicy: sandbox
---
# System Prompt
You are a highly analytical Security and Code Auditor Subagent. You search for vulnerabilities, potential path traversals, or syntax bugs, and can run basic diagnostic tools.
""", encoding="utf-8")

    def get_search_directories(self) -> List[Path]:
        """Returns directories to scan in priority order (later overrides earlier)."""
        home_config_agents = Path.home() / ".config" / "jarvis" / "agents"
        local_repo_agents = self.workspace_root / ".agents" / "agents"

        dirs = []
        # 1. plugins/*/agents/
        plugins_dir = self.workspace_root / "plugins"
        if plugins_dir.exists():
            for p in plugins_dir.iterdir():
                if p.is_dir():
                    agent_p = p / "agents"
                    if agent_p.exists():
                        dirs.append(agent_p)

        # 2. global/machine-wide
        if home_config_agents.exists():
            dirs.append(home_config_agents)

        # 3. repo-local (highest priority)
        if local_repo_agents.exists():
            dirs.append(local_repo_agents)

        return dirs

    def load_agent_from_file(self, path: Path) -> AgentDef:
        """Loads and validates a single agent markdown definition file."""
        try:
            content = path.read_text(encoding="utf-8")
            fm, body = split_frontmatter(content)

            # Ensure name is set, defaulting to filename stem
            if "name" not in fm:
                fm["name"] = path.stem

            agent = AgentDef(**fm, system_prompt=body)

            # Loud load-time validation of declared tools
            unknown = set(agent.tools) - self.tool_registry.known_names()
            if unknown:
                raise AgentLoadError(f"Error loading {path.name}: unknown tool(s) {unknown} declared.")

            return agent
        except Exception as e:
            raise AgentLoadError(f"Failed to load agent at {path}: {e}")

    def load_all(self):
        """Scans all search directories and builds/updates the registry."""
        search_dirs = self.get_search_directories()

        # Keep track of loaded names in this cycle
        active_names = set()

        for dir_path in search_dirs:
            if not dir_path.exists():
                continue
            for file_path in dir_path.glob("*.md"):
                try:
                    mtime = file_path.stat().st_mtime
                    agent_name = file_path.stem

                    # Check if already loaded and mtime is unchanged
                    if agent_name in self._loaded_paths:
                        cached_path, cached_mtime = self._loaded_paths[agent_name]
                        if cached_path == file_path and cached_mtime == mtime:
                            active_names.add(agent_name)
                            continue

                    agent_def = self.load_agent_from_file(file_path)
                    # Register / Override
                    self.agents[agent_def.name] = agent_def
                    self._loaded_paths[agent_def.name] = (file_path, mtime)
                    active_names.add(agent_def.name)
                except Exception as e:
                    # Fail loud on invalid agents
                    print(f"Agent Registry Load Failure: {e}")
                    raise e

        # Remove any deleted files from memory
        deleted_names = set(self.agents.keys()) - active_names
        for name in deleted_names:
            self.agents.pop(name, None)
            self._loaded_paths.pop(name, None)

    def get_agent(self, name: str) -> AgentDef:
        """Returns the AgentDef for the given name. Performs quick hot-reload if files modified."""
        # Cheap hot-reload on fetch
        self.load_all()
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' is not registered.")
        return self.agents[name]

    def list_agents(self) -> List[AgentDef]:
        """Returns list of all loaded AgentDefs."""
        self.load_all()
        return list(self.agents.values())
