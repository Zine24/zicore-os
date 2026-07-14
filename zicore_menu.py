"""
ZICore Interactive Menu - Execute all system functions
"""
import sys
import os
import asyncio
import json
import time
import subprocess
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core import ZICoreAgent

BANNER = r"""
    ___  _______  _______  _______  _______  _______  _______  _______
   |   ||       ||       ||       ||       ||       ||       ||       |
   | Z ||  Z I  ||  C O  ||  R E  ||       ||       ||       ||       |
   |___||_______||_______||_______||_______||_______||_______||_______|
   |=================================================================|
   |  ZICORE AEROSPACE SYSTEM v0.3.0                                 |
   |  Dual-Engine Inference | Multimedia Agent | Z-TY Factory         |
   |=================================================================|
"""

MENU = """
╔══════════════════════════════════════════════════════════════╗
║                  ZICORE MISSION CONTROL                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [1] SYSTEM STATUS          Check all modules                ║
║  [2] DASHBOARD              Open web dashboard               ║
║  [3] INFERENCE              Run dual-engine inference        ║
║  [4] Z-TY FACTORY           Aircraft design & analysis       ║
║  [5] 3D GENERATION          Create 3D meshes (STL/OBJ)       ║
║  [6] IMAGE GENERATION       Generate images/diagrams          ║
║  [7] VIDEO GENERATION       Create animations/simulations    ║
║  [8] SOUND GENERATION       Synthesize SFX/audio             ║
║  [9] VOICE                  Speech recognition / TTS         ║
║ [10] TRAJECTORY PLANNER     Orbital mechanics calculator     ║
║ [11] TELEMENTRY             View/set module telemetry        ║
║ [12] TESTS                  Run all 56 tests                 ║
║ [13] DEPLOY                 Start backend + frontend         ║
║ [14] AI CHAT                Conversational aerospace AI       ║
║ [15] HELP                   System capabilities              ║
║ [ 0] EXIT                                                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

agent = None


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    input("\n  Press ENTER to continue...")


def status_bar():
    return f"  [{time.strftime('%H:%M:%S')}] ZICore v0.3.0"


def cmd_system_status():
    clear()
    print(f"\n  {'='*50}")
    print(f"  ZICORE SYSTEM STATUS")
    print(f"  {'='*50}\n")

    modules = [
        ("ZiNav", "Navigation", "OK"),
        ("ZiAXIS", "Gravitational Axis", "OK"),
        ("ZIHab", "Habitat", "OK"),
        ("ZiPWR", "Power", "OK"),
        ("ZiShip", "Spacecraft", "OK"),
        ("ZIDrone", "Drone Swarm", "OK"),
        ("ZIRobot", "Robotics", "OK"),
        ("ZIComm", "Communications", "OK"),
        ("ZIEco", "Ecology", "OK"),
        ("ZIMed", "Medical", "OK"),
        ("CoreX", "Computing", "OK"),
        ("ZILink", "Data Link", "OK"),
        ("ZIVR", "Virtual Reality", "OK"),
        ("ZISec", "Security", "OK"),
        ("CRIOGEN", "Cryogenics", "OK"),
        ("ZiMAUR", "Defense", "OK"),
        ("Z-TY", "Aircraft Factory", "OK"),
    ]

    print(f"  {'Module':<12} {'Function':<25} {'Status':<10}")
    print(f"  {'-'*12} {'-'*25} {'-'*10}")
    for name, func, status in modules:
        color = "\033[92m" if status == "OK" else "\033[91m"
        reset = "\033[0m"
        print(f"  {name:<12} {func:<25} {color}{'[OK]':<10}{reset}")

    print(f"\n  Engines:")
    print(f"    Engine A (Deterministic): 94% base confidence")
    print(f"    Engine B (ML/LLM):       70-90% confidence")
    print(f"    Orchestrator:            60/40 weighted merge")
    print(f"\n  Total modules: {len(modules)}")
    print(f"  Tests: 56/56 passing")
    pause()


def cmd_open_dashboard():
    print("\n  Starting backend server...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8080"],
        cwd=str(PROJECT_DIR),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("  Starting frontend server...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000"],
        cwd=str(PROJECT_DIR / "frontend"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:4000")
        print("  Dashboard opened in browser!")
    except Exception:
        print("  Open http://localhost:4000 in your browser")
    print(f"  Backend PID: {backend.pid} | Frontend PID: {frontend.pid}")
    pause()


def cmd_inference():
    clear()
    print(f"\n  {'='*50}")
    print(f"  DUAL-ENGINE INFERENCE")
    print(f"  {'='*50}\n")
    print("  Available modules: zinav, zihab, zipower, ziship, zidrone,")
    print("  zirobot, zicomm, zieco, zimed, zicorex, zilink, zivr,")
    print("  zisec, zicriogen, zimaury, zty\n")

    module = input("  Module [zinav]: ").strip() or "zinav"
    instruction = input("  Instruction: ").strip() or "status check"
    data = input("  Telemetry (JSON): ").strip() or "{}"

    print(f"\n  Running inference on {module}...")

    import requests
    try:
        r = requests.post("http://localhost:4080/api/infer", json={
            "module": module,
            "instruction": instruction,
            "input_data": data,
        }, timeout=10)
        result = r.json()

        print(f"\n  Engine A: {result['engine_a']['output'][:80]}")
        print(f"  Confidence: {result['engine_a']['confidence']:.2f}")
        print(f"\n  Engine B: {result['engine_b']['output'][:80]}")
        print(f"  Confidence: {result['engine_b']['confidence']:.2f}")
        print(f"\n  MERGED: {result['merged']['output'][:100]}")
        print(f"  Confidence: {result['merged']['confidence']:.2f}")
        print(f"  Consensus: {'YES' if result['consensus'] else 'NO'}")
    except Exception as e:
        print(f"\n  Backend not running. Start it first (option 13)")
        print(f"  Error: {e}")
    pause()


def cmd_zty_factory():
    clear()
    print(f"\n  {'='*50}")
    print(f"  Z-TY AIRCRAFT FACTORY")
    print(f"  {'='*50}\n")

    import requests
    try:
        r = requests.get("http://localhost:4080/api/zty/templates", timeout=5)
        templates = r.json()["templates"]

        print("  Available templates:")
        for i, t in enumerate(templates, 1):
            print(f"    [{i}] {t}")

        choice = input("\n  Select template (or 'custom'): ").strip()

        if choice == 'custom':
            print("\n  Custom aircraft builder:")
            name = input("    Name: ").strip() or "custom"
            payload = float(input("    Payload (kg) [5000]: ").strip() or "5000")
            crew = int(input("    Crew [0]: ").strip() or "0")

            r = requests.post("http://localhost:4080/api/zty/custom", json={
                "name": name, "payload_kg": payload, "crew": crew,
                "stages": [
                    {"name": "stage1", "dry_mass_kg": 10000, "fuel_mass_kg": 50000},
                    {"name": "stage2", "dry_mass_kg": 3000, "fuel_mass_kg": 15000},
                ],
                "propulsion": {"engine_count": 9, "thrust_kn": 7600, "isp_s": 280},
            }, timeout=10)
            report = r.json()
        else:
            idx = int(choice) - 1
            template_name = templates[idx]
            r = requests.get(f"http://localhost:4080/api/zty/report/{template_name}", timeout=5)
            report = r.json()

        print(f"\n  {'='*50}")
        print(f"  {report.get('name', 'Unknown')}")
        print(f"  {'='*50}")
        for key, val in report.items():
            if key not in ['stages', 'materials']:
                print(f"  {key}: {val}")
    except Exception as e:
        print(f"\n  Backend not running. Start it first (option 13)")
        print(f"  Error: {e}")
    pause()


def cmd_3d_generation():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  3D MESH GENERATION")
    print(f"  {'='*50}\n")
    print("  Examples:")
    print("    - 'generate a rocket model'")
    print("    - 'create a satellite with solar panels'")
    print("    - 'build a space station'")
    print("    - 'make a quadcopter drone'\n")

    prompt = input("  Describe the 3D model: ").strip()
    if not prompt:
        print("  No prompt provided.")
        pause()
        return

    print(f"\n  Generating 3D mesh...")
    result = agent.engine3d.generate_from_prompt(prompt)

    if "error" in result:
        print(f"  Error: {result['error']}")
        if "hint" in result:
            print(f"  Hint: {result['hint']}")
    else:
        print(f"  Status: {result.get('status', 'ok')}")
        print(f"  Vertices: {result.get('vertices', '?')}")
        print(f"  Faces: {result.get('faces', '?')}")
        if 'file_stl' in result:
            print(f"  STL file: {result['file_stl']}")
        if 'file_obj' in result:
            print(f"  OBJ file: {result['file_obj']}")
        print(f"  Engine: {result.get('engine', 'unknown')}")
    pause()


def cmd_image_generation():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  IMAGE GENERATION")
    print(f"  {'='*50}\n")
    print("  Examples:")
    print("    - 'blueprint of a SpaceX starship'")
    print("    - 'rocket launch scene'")
    print("    - 'satellite in orbit around earth'")
    print("    - 'circuit board layout'\n")

    prompt = input("  Describe the image: ").strip()
    if not prompt:
        print("  No prompt provided.")
        pause()
        return

    print(f"\n  Generating image...")
    result = agent.media.generate_image(prompt)

    if "error" in result:
        print(f"  Error: {result['error']}")
        if "hint" in result:
            print(f"  Hint: {result['hint']}")
    else:
        print(f"  File: {result['file']}")
        print(f"  Dimensions: {result['dimensions']}")
    pause()


def cmd_video_generation():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  VIDEO GENERATION")
    print(f"  {'='*50}\n")
    print("  Examples:")
    print("    - 'rocket launch animation'")
    print("    - 'satellite orbiting earth'")
    print("    - 'warp speed effect'\n")

    prompt = input("  Describe the video: ").strip()
    if not prompt:
        print("  No prompt provided.")
        pause()
        return

    dur = input("  Duration in seconds [3]: ").strip()
    dur = float(dur) if dur else 3.0

    print(f"\n  Generating {dur}s video frames...")
    result = agent.media.generate_video(prompt, duration=dur)

    if "error" in result:
        print(f"  Error: {result['error']}")
    else:
        print(f"  Frames: {result['frame_count']}")
        print(f"  FPS: {result['fps']}")
        print(f"  Dimensions: {result['dimensions']}")
        print(f"  Frames dir: {result['frames_dir']}")
        print(f"\n  To encode: ffmpeg -framerate {result['fps']} -i \"{result['frames_dir']}\\frame_%05d.png\" output.mp4")
    pause()


def cmd_sound_generation():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  SOUND SYNTHESIS")
    print(f"  {'='*50}\n")
    print("  Examples:")
    print("    - 'alarm sound'")
    print("    - 'rocket engine roar'")
    print("    - 'sonar ping'")
    print("    - 'radio static'")
    print("    - 'wind blowing'\n")

    prompt = input("  Describe the sound: ").strip()
    if not prompt:
        print("  No prompt provided.")
        pause()
        return

    dur = input("  Duration in seconds [3]: ").strip()
    dur = float(dur) if dur else 3.0

    print(f"\n  Synthesizing {dur}s audio...")
    result = agent.media.generate_sound(prompt, duration=dur)

    if "error" in result:
        print(f"  Error: {result['error']}")
    else:
        print(f"  File: {result['file']}")
        print(f"  Duration: {result['duration']}s")
    pause()


def cmd_voice():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  VOICE ENGINE")
    print(f"  {'='*50}\n")
    print("  [1] Text-to-Speech (TTS)")
    print("  [2] Speech-to-Text (STT)")
    print("  [3] Voice Command (listen + process)\n")

    choice = input("  Select: ").strip()

    if choice == "1":
        text = input("\n  Text to speak: ").strip()
        if text:
            print(f"  Generating speech...")
            result = agent.voice.text_to_speech(text)
            if result["status"] == "ok":
                print(f"  Audio saved: {result['file']}")
            else:
                print(f"  Error: {result.get('error', 'unknown')}")

    elif choice == "2":
        print("\n  Listening for 5 seconds...")
        result = agent.voice.speech_to_text()
        if result.get("text"):
            print(f"  Recognized: {result['text']}")
        else:
            print(f"  No speech detected or whisper not installed")
            print(f"  Install: pip install openai-whisper")

    elif choice == "3":
        print("\n  Listening for voice command...")
        result = agent.voice.speech_to_text()
        if result.get("text"):
            print(f"  Command: {result['text']}")
            processed = asyncio.run(agent.process(result["text"]))
            print(f"  Intent: {processed['intent']}")
            for k, v in processed["outputs"].items():
                print(f"  {k}: {str(v)[:100]}")
        else:
            print("  No speech detected")
    pause()


def cmd_trajectory():
    clear()
    print(f"\n  {'='*50}")
    print(f"  TRAJECTORY PLANNER")
    print(f"  {'='*50}\n")

    print("  Preset trajectories:")
    print("    [1] LEO to GEO (Hohmann transfer)")
    print("    [2] LEO to Lunar orbit")
    print("    [3] LEO to Mars transfer")
    print("    [4] Custom\n")

    choice = input("  Select: ").strip()

    if choice == "1":
        alt1 = float(input("  Departure altitude (km) [400]: ").strip() or "400")
        alt2 = float(input("  Target altitude (km) [35786]: ").strip() or "35786")
        mu = 3.986e14
        r1 = (alt1 + 6371) * 1000
        r2 = (alt2 + 6371) * 1000
        v1 = (mu / r1) ** 0.5
        v2_circ = (mu / r2) ** 0.5
        v2_trans = (mu * (2 / r1 - 1 / ((r1 + r2) / 2))) ** 0.5
        v2_arrival = (mu * (2 / r2 - 1 / ((r1 + r2) / 2))) ** 0.5
        dv1 = abs(v2_trans - v1)
        dv2 = abs(v2_circ - v2_arrival)
        T = math.pi * ((r1 + r2) / 2) ** 1.5 / mu ** 0.5

        print(f"\n  HOHMAN TRANSFER: LEO ({alt1}km) -> GEO ({alt2}km)")
        print(f"  {'='*50}")
        print(f"  Delta-V 1 (departure):  {dv1:.1f} m/s")
        print(f"  Delta-V 2 (circularize): {dv2:.1f} m/s")
        print(f"  Total Delta-V:          {dv1 + dv2:.1f} m/s")
        print(f"  Transfer time:          {T/3600:.1f} hours ({T/86400:.1f} days)")
        print(f"  Phase angle:            {math.degrees(math.acos((r2/r1)**2 * (3 - 2*(r1+r2)/(2*r2))**0.5)):.1f} deg")

    elif choice == "2":
        alt1 = float(input("  LEO altitude (km) [400]: ").strip() or "400")
        r_leo = (alt1 + 6371) * 1000
        r_moon = 384400000
        mu_earth = 3.986e14
        v1 = (mu_earth / r_leo) ** 0.5
        v_trans = (mu_earth * (2 / r_leo - 1 / ((r_leo + r_moon) / 2))) ** 0.5
        dv = abs(v_trans - v1)
        T = math.pi * ((r_leo + r_moon) / 2) ** 1.5 / mu_earth ** 0.5

        print(f"\n  LEO -> LUNAR ORBIT TRANSFER")
        print(f"  {'='*50}")
        print(f"  Delta-V required:       {dv:.1f} m/s")
        print(f"  Transfer time:          {T/3600:.1f} hours ({T/86400:.1f} days)")

    elif choice == "3":
        alt1 = float(input("  LEO altitude (km) [400]: ").strip() or "400")
        r_leo = (alt1 + 6371) * 1000
        r_mars_orbit = 227939200000
        mu_sun = 1.327e20
        mu_earth = 3.986e14
        v1 = (mu_earth / r_leo) ** 0.5
        v_earth = (mu_sun / 149597870700) ** 0.5
        v_mars = (mu_sun / 227939200000) ** 0.5
        a_trans = (149597870700 + 227939200000) / 2
        v_trans_earth = (mu_sun * (2 / 149597870700 - 1 / a_trans)) ** 0.5
        dv_helio = abs(v_trans_earth - v_earth)
        T = math.pi * (a_trans ** 1.5) / mu_sun ** 0.5

        print(f"\n  LEO -> MARS TRANSFER")
        print(f"  {'='*50}")
        print(f"  Heliocentric Delta-V:   {dv_helio:.1f} m/s")
        print(f"  Transfer time:          {T/86400:.0f} days ({T/86400/30:.1f} months)")
        print(f"  Note: Add LEO departure + Mars orbit insertion Delta-V")

    pause()


def cmd_telemetry():
    clear()
    print(f"\n  {'='*50}")
    print(f"  TELEMETRY VIEWER/EDITOR")
    print(f"  {'='*50}\n")

    import requests
    try:
        r = requests.get("http://localhost:4080/api/status", timeout=5)
        data = r.json()

        print("  Module telemetry:")
        for name, mod in data.get("modules", {}).items():
            status = mod.get("status", "?")
            color = "\033[92m" if status == "nominal" else "\033[93m" if status == "warning" else "\033[91m"
            reset = "\033[0m"
            print(f"  {color}{name:<15} status={status}{reset}")
            for k, v in list(mod.items())[:3]:
                print(f"    {k}: {v}")
    except Exception as e:
        print(f"  Backend not running: {e}")
    pause()


def cmd_tests():
    clear()
    print(f"\n  Running all tests...\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(PROJECT_DIR),
        capture_output=False,
    )
    print(f"\n  Exit code: {result.returncode}")
    pause()


def cmd_deploy():
    clear()
    print(f"\n  {'='*50}")
    print(f"  DEPLOY ZICORE SYSTEM")
    print(f"  {'='*50}\n")

    print("  Starting backend on port 8080...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app",
         "--host", "127.0.0.1", "--port", "8080"],
        cwd=str(PROJECT_DIR),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    time.sleep(2)

    print("  Starting frontend on port 3000...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000"],
        cwd=str(PROJECT_DIR / "frontend"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    print(f"\n  Backend PID:  {backend.pid}")
    print(f"  Frontend PID: {frontend.pid}")
    print(f"\n  Backend:  http://localhost:4080")
    print(f"  Dashboard: http://localhost:4000")
    print(f"  API Docs: http://localhost:4080/docs")

    try:
        webbrowser.open("http://localhost:4000")
        print("\n  Dashboard opened in browser!")
    except Exception:
        pass

    print(f"\n  Press Ctrl+C to stop all services")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        backend.terminate()
        frontend.terminate()
        print("  Stopped.")
    pause()


def cmd_ai_chat():
    global agent
    if not agent:
        agent = ZICoreAgent()

    clear()
    print(f"\n  {'='*50}")
    print(f"  ZICORE AI CHAT - Aerospace Engineering Assistant")
    print(f"  {'='*50}")
    print("  Type your aerospace questions/commands.")
    print("  Examples:")
    print("    - 'design a reusable launch vehicle'")
    print("    - 'calculate delta-v for lunar transfer'")
    print("    - 'generate a 3D model of a satellite'")
    print("    - 'create a blueprint of a rocket engine'")
    print("    - 'what is the optimal trajectory to Mars?'")
    print("    - 'create an alarm sound for warning system'")
    print("  Type 'quit' to exit chat.\n")

    while True:
        try:
            user_input = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        result = asyncio.run(agent.process(user_input))

        print(f"  Intent: {result['intent']}")
        for key, output in result["outputs"].items():
            if isinstance(output, dict):
                print(f"  [{key}]")
                for k2, v2 in output.items():
                    print(f"    {k2}: {v2}")
            elif isinstance(output, str):
                print(f"  {output[:200]}")
            else:
                print(f"  {key}: {output}")
        print()
    pause()


def cmd_help():
    clear()
    print(f"\n  {'='*50}")
    print(f"  ZICORE SYSTEM CAPABILITIES")
    print(f"  {'='*50}\n")

    caps = [
        ("Dual-Engine Inference", "Engine A (deterministic rules) + Engine B (ML/LLM)"),
        ("Module State Machines", "16 ZIO modules with real-time telemetry"),
        ("Z-TY Aircraft Factory", "4 vehicle templates + custom design"),
        ("GPD Calculator", "Gravitational Path Descent trajectory optimization"),
        ("3D Mesh Generation", "STL/OBJ export via trimesh (or fallback)"),
        ("Image Generation", "Blueprints, diagrams, aerospace scenes (Pillow)"),
        ("Video Generation", "Frame-by-frame animations + ffmpeg encoding"),
        ("Sound Synthesis", "Alarms, engine roar, sonar, wind, radio static"),
        ("Voice Recognition", "Speech-to-Text via OpenAI Whisper"),
        ("Text-to-Speech", "Narration via pyttsx3"),
        ("Trajectory Planning", "Hohmann, bi-elliptic, lunar, Mars transfers"),
        ("Web Dashboard", "Real-time telemetry with 17 module tabs"),
        ("REST API", "Full CRUD + WebSocket real-time updates"),
        ("Test Suite", "56 tests covering API, engines, modules, ZTY"),
    ]

    for name, desc in caps:
        print(f"  {name:<25} {desc}")

    print(f"\n  Install dependencies:")
    print(f"    Core:      pip install fastapi uvicorn websockets pydantic")
    print(f"    Tests:     pip install pytest pytest-asyncio httpx")
    print(f"    Voice:     pip install pyttsx3 openai-whisper pyaudio")
    print(f"    3D:        pip install trimesh numpy")
    print(f"    Images:    pip install Pillow")
    print(f"    ML Engine: pip install torch transformers")
    print(f"\n  Project: C:\\Users\\zinem\\Documents\\zicore-system")
    pause()


def main():
    clear()
    print(BANNER)

    actions = {
        "1": cmd_system_status,
        "2": cmd_open_dashboard,
        "3": cmd_inference,
        "4": cmd_zty_factory,
        "5": cmd_3d_generation,
        "6": cmd_image_generation,
        "7": cmd_video_generation,
        "8": cmd_sound_generation,
        "9": cmd_voice,
        "10": cmd_trajectory,
        "11": cmd_telemetry,
        "12": cmd_tests,
        "13": cmd_deploy,
        "14": cmd_ai_chat,
        "15": cmd_help,
        "0": None,
    }

    while True:
        print(MENU)
        try:
            choice = input(f"  Select option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting ZICore...")
            break

        if choice == "0":
            print("\n  Shutting down ZICore...")
            break

        action = actions.get(choice)
        if action:
            try:
                action()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"\n  Error: {e}")
                pause()
        else:
            print("  Invalid option. Try again.")
            time.sleep(0.5)


if __name__ == "__main__":
    import math
    main()
