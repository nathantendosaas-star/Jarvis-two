"""
Terminal output helpers. Uses colorama so colors actually work in
Windows cmd.exe, not just Unix terminals.
"""

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    _HAS_COLOR = False

    class _Dummy:
        def __getattr__(self, name):
            return ""

    Fore = _Dummy()
    Style = _Dummy()


def agent_say(text):
    print(f"\n{Fore.CYAN}[Agent]{Style.RESET_ALL}\n{text}")


def sub_agent_say(depth, text):
    indent = "  " * depth
    print(f"{Fore.MAGENTA}{indent}[Subagent L{depth}]{Style.RESET_ALL} {text}")


def tool_say(name, detail=""):
    detail = (detail or "")[:200]
    print(f"{Fore.YELLOW}[tool] {name}{Style.RESET_ALL} {detail}")


def tool_result_say(text, limit=1500):
    text = text or ""
    preview = text if len(text) <= limit else text[:limit] + "\n...[truncated]"
    print(f"{Style.DIM}{preview}{Style.RESET_ALL}")


def plan_say(steps):
    print(f"\n{Fore.GREEN}[plan]{Style.RESET_ALL}")
    for s in steps:
        status = s.get("status", "pending")
        mark = "x" if status == "done" else (">" if status == "in_progress" else " ")
        print(f"  [{mark}] {s.get('id', '?')}. {s.get('text', '')}")
    print()


def think_say(text, limit=500):
    if not text:
        return
    preview = text if len(text) <= limit else text[:limit] + "..."
    print(f"{Style.DIM}[thinking] {preview}{Style.RESET_ALL}")


def warn(text):
    print(f"{Fore.RED}[!] {text}{Style.RESET_ALL}")


def error(text):
    print(f"{Fore.RED}[error] {text}{Style.RESET_ALL}")
