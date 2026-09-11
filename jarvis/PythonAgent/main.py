"""
Entry point. Run with:  python main.py
"""

import config
import ui
from agent import Agent


def main():
    config.check_setup()

    print("=" * 64)
    print(" Agent CLI -- DeepSeek V4 Flash via OpenRouter")
    print(" Commands: 'exit' to quit, '/plan' to view the current plan,")
    print("           '/auto' to toggle auto-approve for safe commands")
    print("=" * 64)

    agent = Agent()

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            break

        if user_input == "/plan":
            if agent.plan:
                ui.plan_say(agent.plan)
            else:
                print("No active plan.")
            continue

        if user_input == "/auto":
            config.AUTO_APPROVE = not config.AUTO_APPROVE
            print(f"Auto-approve is now {'ON' if config.AUTO_APPROVE else 'OFF'}.")
            continue

        try:
            agent.run_turn(user_input)
        except Exception as e:
            ui.error(str(e))


if __name__ == "__main__":
    main()
