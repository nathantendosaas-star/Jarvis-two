import re
import os
import yaml
from pathlib import Path
from typing import List, Literal, Optional, Set, Dict, Any
from pydantic import BaseModel

class PermissionConfig(BaseModel):
    allow: List[str] = []
    deny: List[str] = []
    ask: List[str] = ["*"]  # Default fallback for anything unmatched

class PermissionSet:
    def __init__(
        self,
        config: PermissionConfig,
        command_execution: Literal["off", "auto", "eager", "sandbox"] = "sandbox",
        sandbox_enabled: bool = True,
        workspace_root: Optional[Path] = None
    ):
        self.config = config
        self.command_execution = command_execution
        self.sandbox_enabled = sandbox_enabled
        self.workspace_root = workspace_root or Path.cwd().resolve()

    def check_pattern_match(self, pattern: str, action: str) -> bool:
        """Helper to match action against a pattern supporting simple wildcards or regex."""
        if pattern == "*":
            return True
        try:
            # Escape the pattern to ensure parenthesis, brackets, etc. are matched literally
            escaped_pat = re.escape(pattern)
            # Convert escaped wildcards back to regex.
            regex_pat = escaped_pat.replace(r"\.\*", ".*").replace(r"\*", ".*")

            return bool(re.search(regex_pat, action, re.IGNORECASE))
        except Exception:
            # Fallback to direct substring match if regex compilation fails
            return pattern.lower() in action.lower()

    def resolve(self, action: str) -> Literal["allow", "deny", "ask"]:
        """Resolves rule for action based on resolution order: deny > allow > ask."""
        # 1. Deny always wins
        for pat in self.config.deny:
            if self.check_pattern_match(pat, action):
                return "deny"

        # 2. Allow matches
        for pat in self.config.allow:
            if self.check_pattern_match(pat, action):
                return "allow"

        # 3. Ask matches
        for pat in self.config.ask:
            if self.check_pattern_match(pat, action):
                return "ask"

        # Default fallback
        return "ask"

def policy_strictness_rank(policy: str) -> int:
    ranks = {"off": 0, "sandbox": 1, "auto": 2, "eager": 3}
    return ranks.get(policy, 1)

def permission_rank(decision: Literal["allow", "deny", "ask"]) -> int:
    ranks = {"deny": 0, "ask": 1, "allow": 2}
    return ranks.get(decision, 1)

def intersect_permissions(parent: PermissionSet, child_declared_config: PermissionConfig, child_command_policy: str) -> PermissionSet:
    """Creates a Child PermissionSet that is strictly the intersection of parent rules and child def's limits."""
    # Child permission set is wrapper that evaluates both parent permissions and child permissions,
    # returning the strictest of the two (the intersection).

    # We rank decision outcome: deny (0) < ask (1) < allow (2)
    # The effective permission is the minimum rank of parent and child.

    child_permissions = PermissionSet(
        config=child_declared_config,
        command_execution=child_command_policy, # Placeholder, resolved dynamically
        sandbox_enabled=parent.sandbox_enabled or child_command_policy == "sandbox",
        workspace_root=parent.workspace_root
    )

    # Let's override resolve to perform live intersection
    original_resolve = child_permissions.resolve

    def intersected_resolve(action: str) -> Literal["allow", "deny", "ask"]:
        parent_decision = parent.resolve(action)
        child_decision = original_resolve(action)

        parent_r = permission_rank(parent_decision)
        child_r = permission_rank(child_decision)

        # Intersect command policies specifically for command actions
        if action.startswith("command"):
            if child_permissions.command_execution == "off":
                return "deny"
            if parent.command_execution == "off":
                return "deny"
            # If sandbox is enabled on parent, child must run inside sandbox

        final_rank = min(parent_r, child_r)
        if final_rank == 0:
            return "deny"
        elif final_rank == 1:
            return "ask"
        return "allow"

    child_permissions.resolve = intersected_resolve

    # Resolve exact command_execution policy (least permissive wins)
    child_permissions.command_execution = min(
        parent.command_execution,
        child_command_policy,
        key=policy_strictness_rank
    )
    child_permissions.sandbox_enabled = parent.sandbox_enabled or child_command_policy == "sandbox"

    return child_permissions

def load_permission_config(workspace_root: Optional[Path] = None) -> PermissionConfig:
    """Loads permission config from repo-local or global user config paths, falling back to sane defaults."""
    workspace_root = workspace_root or Path.cwd().resolve()

    search_paths = [
        workspace_root / ".agents" / "permissions.yaml",
        workspace_root / ".agents" / "permissions.yml",
        Path.home() / ".config" / "jarvis" / "permissions.yaml",
        Path.home() / ".config" / "jarvis" / "permissions.yml",
    ]

    for path in search_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return PermissionConfig(
                            allow=data.get("allow", []),
                            deny=data.get("deny", []),
                            ask=data.get("ask", ["*"])
                        )
            except Exception as e:
                print(f"Error loading permission config at {path}: {e}")

    # Return standard default config
    return PermissionConfig(
        allow=[],
        deny=[],
        ask=["*"]
    )
