import os
import sys
import json
import re
import subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

# --- 1. LOCK WORKSPACE TO PROJECT FOLDER ---
# This ensures files are ALWAYS saved in your 'E:\\nate\\GEMINI AGENT\\JARVIS' folder
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def list_directory():
    """Lists files in the project folder."""
    try:
        files = os.listdir(WORKSPACE_DIR)
        return f"Files in project folder: {files}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_file(filename):
    """Reads the contents of a file inside the project folder."""
    filepath = os.path.join(WORKSPACE_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f"--- CONTENT OF {filename} ---\n{f.read()}"
    except Exception as e:
        return f"Error reading file {filename}: {str(e)}"

def write_file(filename, content):
    """Creates or overwrites a file inside the project folder."""
    filepath = os.path.join(WORKSPACE_DIR, filename)
    try:
        # Ensure any subdirectories inside the project folder are created
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: Written content to target file: '{filepath}'."
    except Exception as e:
        return f"Error writing to file {filename}: {str(e)}"

def execute_command(command):
    """Executes a terminal/shell command inside the project folder."""
    if any(x in command.lower() for x in ["rmdir /s", "del /f", "format"]):
        return "Error: Command blocked for system safety."
    try:
        # Run command specifically inside the project folder directory (cwd)
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=WORKSPACE_DIR, 
            capture_output=True, 
            text=True, 
            timeout=15
        )
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        return f"Exit Code: {result.returncode}\nSTDOUT:\n{output}\nSTDERR:\n{error}"
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out (15s limit)."
    except Exception as e:
        return f"Error executing command: {str(e)}"

# Map string names to the actual python functions
TOOLS = {
    "list_directory": list_directory,
    "read_file": read_file,
    "write_file": write_file,
    "execute_command": execute_command
}

# --- 2. THE SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are JARVIS, a highly capable local agent running on Windows.
You can think, plan, and execute actions using tools. 

You have access to the following tools:
- list_directory() -> Returns files in the current workspace.
- read_file(filename) -> Reads file contents.
- write_file(filename, content) -> Creates/overwrites a file.
- execute_command(command) -> Runs a shell command on the host machine.

You must operate in a strict loop: Thought, Action, Observation.
Use the EXACT format below. Do not output anything else.

Thought: What you need to do next to solve the user's request.
Action: Name of the tool to use (must be one of: list_directory, read_file, write_file, execute_command).
Arguments: The exact argument(s) for the tool. Use JSON format for arguments.
Observation: [The system will run the tool and show you the output here. DO NOT write this part yourself.]

Once you have completely finished the task, output:
Final Answer: [Your brief summary of what was accomplished]
"""

# --- 3. RUNNING THE AGENT LOOP ---
def query_ollama(prompt_history):
    payload = {
        "model": "jarvis-local",
        "prompt": prompt_history,
        "stream": False,
        "options": {
            "temperature": 0.1 # Very low temp for strict format adherence
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        return response.json().get("response", "")
    except Exception as e:
        print(f"Connection Error: {e}")
        return ""

def run_agentic_workflow(user_goal, conversation_history):
    print(f"\n🚀 Starting Agentic Workflow: '{user_goal}'")
    
    # Active workspace history for this specific run
    active_history = f"{conversation_history}\nUser Goal: {user_goal}\n"
    
    max_steps = 8  # Safety cutoff to prevent infinite loops
    final_answer = "No final answer was reached."
    
    for step in range(1, max_steps + 1):
        print(f"\n--- [Step {step}] Thinking... ---")
        
        # 1. Ask the model what to do next
        response = query_ollama(active_history)
        print(response)
        
        active_history += response + "\n"
        
        # Check if finished
        if "Final Answer:" in response:
            print("\n✔️ TASK COMPLETE!")
            # Grab the final answer text
            match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
            if match:
                final_answer = match.group(1).strip()
            else:
                final_answer = response
            break
            
        # 2. Parse the Action and Arguments
        action_match = re.search(r"Action:\s*(\w+)", response)
        args_match = re.search(r"Arguments:\s*(.*)", response)
        
        if action_match and args_match:
            tool_name = action_match.group(1).strip()
            args_str = args_match.group(1).strip()
            
            if tool_name in TOOLS:
                try:
                    args = json.loads(args_str)
                    print(f"🔧 Executing Tool [{tool_name}]...")
                    
                    if isinstance(args, dict):
                        observation = TOOLS[tool_name](**args)
                    else:
                        observation = TOOLS[tool_name](args)
                        
                except Exception as e:
                    observation = f"Error parsing arguments or executing tool: {str(e)}"
            else:
                observation = f"Error: Tool '{tool_name}' does not exist."
        else:
            observation = "Error: Could not parse Action/Arguments. Please output in the correct format."
            
        print(f"👁️ Observation:\n{observation}")
        active_history += f"Observation: {observation}\n"
        
    else:
        print("\n❌ Reached maximum step limit without resolving the task.")
        
    return final_answer

# --- 4. THE CONTINUOUS WORKSPACE LOOP ---
def main():
    # Initialize the base conversation with our system prompt
    conversation_history = SYSTEM_PROMPT + "\n"
    
    print("🤖 JARVIS Local Agent Online. Type 'exit' or 'quit' to close.")
    print(f"📂 Project Folder Locked: {WORKSPACE_DIR}\n")
    
    while True:
        try:
            # Continuous Prompt Input
            user_goal = input("\nJARVIS > ")
            
            if user_goal.strip().lower() in ["exit", "quit"]:
                print("Exiting JARVIS. Goodbye!")
                break
                
            if not user_goal.strip():
                continue
            
            # Run the agentic workflow and extract the clean final summary
            final_answer = run_agentic_workflow(user_goal, conversation_history)
            
            # MEMORY COMPRESSION: We append only the Goal and Final Answer to the running history.
            # This discards the raw Thinking/Action logs of previous steps to save huge RAM/Tokens!
            conversation_history += f"\nUser Goal: {user_goal}\nFinal Answer: {final_answer}\n"
            
        except KeyboardInterrupt:
            print("\nExiting JARVIS. Goodbye!")
            break

if __name__ == "__main__":
    main()