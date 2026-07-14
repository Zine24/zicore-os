#!/usr/bin/env python3
"""
ZICORE Agent CLI - Interactive command-line interface
"""
import sys
import os
import json
import asyncio
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.core import ZICoreAgent
from agent.state import SessionManager, ContextMemory, ToolRegistry


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  ZICORE AGENT CLI v3.7                                      ║
║  Aerospace Intelligence System                              ║
║  Type 'help' for commands, 'exit' to quit                   ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  help                    Show this help message
  status                  Show system status
  capabilities            List agent capabilities
  history                 Show conversation history
  clear                   Clear conversation history
  
  # Inference
  infer <module> <msg>    Run inference on a module
  trajectory <msg>        Calculate trajectory
  aircraft <msg>          Design aircraft
  
  # Tools
  tools                   List available tools
  tool <name> <args>      Call a tool
  
  # Media
  image <prompt>          Generate image
  video <prompt>          Generate video
  sound <prompt>          Generate sound
  3d <prompt>             Generate 3D model
  tts <text>              Text to speech
  
  # System
  modules                 List all modules
  telemetry <module>      Get module telemetry
  gpd                     Run GPD calculation
  
  # Session
  session                 Show current session
  sessions                List all sessions
  export                  Export session data
  
  exit / quit             Exit CLI
"""


class AgentCLI:
    def __init__(self, api_url: str = "http://localhost:4080"):
        self.api_url = api_url
        self.agent = ZICoreAgent()
        self.session_id = f"cli_{os.getpid()}"
        self.running = True
        self.history = []

    def print_colored(self, text: str, color: str = "white"):
        colors = {
            "cyan": "\033[96m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "magenta": "\033[95m",
            "blue": "\033[94m",
            "white": "\033[0m",
            "gray": "\033[90m",
        }
        c = colors.get(color, "")
        print(f"{c}{text}\033[0m")

    def print_response(self, response: dict):
        intent = response.get("intent", "general")
        outputs = response.get("outputs", {})
        latency = response.get("latency_ms", 0)

        self.print_colored(f"\n[Intent: {intent}] [{latency:.1f}ms]", "gray")

        if "text" in outputs:
            self.print_colored(outputs["text"], "cyan")
        elif "inference" in outputs:
            inf = outputs["inference"]
            self.print_colored(f"Engine: {inf.get('engine', '?')}", "green")
            self.print_colored(f"Confidence: {inf.get('confidence', 0):.2f}", "green")
            self.print_colored(f"Result: {json.dumps(inf.get('result', {}), indent=2)[:500]}", "cyan")
        elif "trajectory" in outputs:
            tr = outputs["trajectory"]
            self.print_colored(f"Type: {tr.get('type', '?')}", "yellow")
            self.print_colored(f"Delta-V: {tr.get('delta_v_ms', 0)} m/s", "yellow")
            self.print_colored(f"Time: {tr.get('time_days', 0)} days", "yellow")
        elif "aircraft" in outputs:
            ac = outputs["aircraft"]
            self.print_colored(f"Name: {ac.get('name', '?')}", "magenta")
            self.print_colored(f"Type: {ac.get('type', '?')}", "magenta")
            self.print_colored(f"Payload: {ac.get('payload_kg', 0)} kg", "magenta")
        else:
            self.print_colored(json.dumps(outputs, indent=2)[:1000], "cyan")

    async def process_command(self, line: str) -> bool:
        line = line.strip()
        if not line:
            return True

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        self.history.append({"role": "user", "content": line})

        if cmd in ("exit", "quit", "q"):
            self.running = False
            return False

        elif cmd == "help":
            self.print_colored(HELP_TEXT, "white")

        elif cmd == "status":
            try:
                import httpx
                r = httpx.get(f"{self.api_url}/api/status")
                data = r.json()
                self.print_colored(f"Status: {data.get('status', '?')}", "green")
                self.print_colored(f"Modules: {len(data.get('modules', {}))}", "green")
                self.print_colored(f"Engines: {json.dumps(data.get('engines', {}))}", "cyan")
            except Exception as e:
                self.print_colored(f"Backend offline: {e}", "red")

        elif cmd == "capabilities":
            caps = self.agent.get_capabilities()
            self.print_colored("Agent Capabilities:", "yellow")
            for cat, items in caps.items():
                self.print_colored(f"  {cat}:", "green")
                if isinstance(items, list):
                    for item in items:
                        self.print_colored(f"    - {item}", "white")
                elif isinstance(items, dict):
                    for k, v in items.items():
                        self.print_colored(f"    {k}: {v}", "white")

        elif cmd == "history":
            self.print_colored("Conversation History:", "yellow")
            for h in self.history[-20:]:
                role = h.get("role", "?")
                color = "cyan" if role == "user" else "green"
                self.print_colored(f"  [{role}] {h.get('content', '')[:100]}", color)

        elif cmd == "clear":
            self.history.clear()
            self.print_colored("History cleared", "green")

        elif cmd == "infer":
            module = args.split(maxsplit=1)[0] if args else "zicorex"
            msg = args.split(maxsplit=1)[1] if " " in args else "status check"
            response = await self.agent.process_message(msg, self.session_id)
            self.print_response(response)

        elif cmd == "trajectory":
            response = await self.agent.process_message(f"calculate trajectory: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "aircraft":
            response = await self.agent.process_message(f"design aircraft: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "tools":
            tools = self.agent.tool_registry.list_tools()
            self.print_colored("Available Tools:", "yellow")
            for t in tools:
                self.print_colored(f"  {t['name']}: {t.get('description', '')}", "white")

        elif cmd == "tool":
            if not args:
                self.print_colored("Usage: tool <name> <args>", "red")
            else:
                tool_parts = args.split(maxsplit=1)
                tool_name = tool_parts[0]
                tool_args = tool_parts[1] if len(tool_parts) > 1 else "{}"
                try:
                    args_dict = json.loads(tool_args) if tool_args.startswith("{") else {"input": tool_args}
                    result = self.agent.tool_registry.call_tool(tool_name, **args_dict)
                    self.print_colored(json.dumps(result, indent=2), "cyan")
                except Exception as e:
                    self.print_colored(f"Tool error: {e}", "red")

        elif cmd == "image":
            response = await self.agent.process_message(f"generate image: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "video":
            response = await self.agent.process_message(f"generate video: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "sound":
            response = await self.agent.process_message(f"generate sound: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "3d":
            response = await self.agent.process_message(f"generate 3d model: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "tts":
            response = await self.agent.process_message(f"text to speech: {args}", self.session_id)
            self.print_response(response)

        elif cmd == "modules":
            self.print_colored("ZICORE Modules:", "yellow")
            modules = [
                "zinav", "zihab", "zipower", "ziship", "zidrone", "zirobot",
                "zicomm", "zieco", "zimed", "zicorex", "zilink", "zivr",
                "zisec", "zicriogen", "zimaury", "zty"
            ]
            for m in modules:
                self.print_colored(f"  {m}", "cyan")

        elif cmd == "telemetry":
            module = args if args else "zicorex"
            try:
                import httpx
                r = httpx.get(f"{self.api_url}/api/telemetry/{module}")
                data = r.json()
                self.print_colored(f"Module: {module}", "yellow")
                self.print_colored(json.dumps(data, indent=2), "cyan")
            except Exception as e:
                self.print_colored(f"Error: {e}", "red")

        elif cmd == "gpd":
            try:
                import httpx
                r = httpx.get(f"{self.api_url}/api/hierarchy")
                data = r.json()
                self.print_colored("GPD Hierarchy:", "yellow")
                self.print_colored(json.dumps(data, indent=2), "cyan")
            except Exception as e:
                self.print_colored(f"Error: {e}", "red")

        elif cmd == "session":
            self.print_colored(f"Session ID: {self.session_id}", "green")
            self.print_colored(f"History: {len(self.history)} messages", "green")

        elif cmd == "sessions":
            try:
                import httpx
                r = httpx.get(f"{self.api_url}/api/agent/sessions")
                data = r.json()
                for s in data.get("sessions", []):
                    self.print_colored(f"  {s['id']}: {s['messages']} msgs", "white")
            except Exception as e:
                self.print_colored(f"Error: {e}", "red")

        elif cmd == "export":
            export_file = Path("output") / f"session_{self.session_id}.json"
            export_file.parent.mkdir(exist_ok=True)
            with open(export_file, "w") as f:
                json.dump(self.history, f, indent=2)
            self.print_colored(f"Exported to {export_file}", "green")

        else:
            # Treat as natural language query
            response = await self.agent.process_message(line, self.session_id)
            self.print_response(response)

        return True

    async def run(self):
        self.print_colored(BANNER, "cyan")
        self.print_colored(f"Session: {self.session_id}", "gray")
        self.print_colored("Type 'help' for commands\n", "gray")

        while self.running:
            try:
                line = input("\033[96mzio>\033[0m ").strip()
                if not line:
                    continue
                if not await self.process_command(line):
                    break
            except KeyboardInterrupt:
                self.print_colored("\n\nInterrupted", "yellow")
                self.running = False
            except EOFError:
                break

        self.print_colored("\nGoodbye!", "cyan")


def main():
    parser = argparse.ArgumentParser(description="ZICORE Agent CLI")
    parser.add_argument("--url", default="http://localhost:4080", help="Backend URL")
    parser.add_argument("--cmd", help="Run a single command and exit")
    args = parser.parse_args()

    cli = AgentCLI(api_url=args.url)

    if args.cmd:
        asyncio.run(cli.process_command(args.cmd))
    else:
        asyncio.run(cli.run())


if __name__ == "__main__":
    main()
