class NestingLimitExceeded(Exception):
    def __init__(self, message="Maximum nesting depth of 10 reached."):
        super().__init__(message)

class TooManyChildren(Exception):
    def __init__(self, message="Maximum concurrent subagents per parent (8) exceeded."):
        super().__init__(message)

class GlobalAgentLimitExceeded(Exception):
    def __init__(self, message="Global agent limit of 50 active agents exceeded."):
        super().__init__(message)

class StuckLoopDetected(Exception):
    def __init__(self, message="Execution aborted: Agent detected in an infinite loop repeating the same action."):
        super().__init__(message)


MAX_NESTING_DEPTH = 10
MAX_CONCURRENT_CHILDREN_PER_PARENT = 8
MAX_TOTAL_LIVE_AGENTS = 50


def check_spawn_allowed(caller_depth: int, caller_children_count: int, live_agents_count: int):
    """Enforces nesting, child count, and global active agent circuit breakers."""
    if caller_depth + 1 > MAX_NESTING_DEPTH:
        raise NestingLimitExceeded()

    if caller_children_count >= MAX_CONCURRENT_CHILDREN_PER_PARENT:
        raise TooManyChildren()

    if live_agents_count >= MAX_TOTAL_LIVE_AGENTS:
        raise GlobalAgentLimitExceeded()
