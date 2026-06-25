#!/usr/bin/env python3
"""
ZiCore Mission Control — Lanza backend, frontend y monitores en una sola terminal.
"""
import subprocess, sys, os, time, json, webbrowser, threading, signal

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_PORT = 8080
FRONTEND_PORT = 3000

backend_proc = None
frontend_proc = None

ANSI = {
    "green": "\033[32m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "reset": "\033[0m",
}
USE_COLOR = sys.stdout.isatty()

def log(color, msg):
    c = ANSI.get(color, "")
    r = ANSI["reset"] if USE_COLOR else ""
    print(f"{c}[ZiCore]{r} {msg}")

def check_deps():
    log("cyan", "Verificando dependencias...")
    missing = []
    for cmd in ["python", "pip"]:
        r = subprocess.run(["where", cmd] if sys.platform == "win32" else ["which", cmd],
                           capture_output=True, shell=True)
        if r.returncode != 0:
            missing.append(cmd)
    if missing:
        log("red", f"Faltan: {', '.join(missing)}. Instalelos primero.")
        sys.exit(1)
    for f in ["backend/app/main.py", "frontend/dashboard.html"]:
        if not os.path.isfile(os.path.join(ROOT, f)):
            log("red", f"No se encuentra: {f}. Ejecute desde el directorio del proyecto.")
            sys.exit(1)
    log("green", "Dependencias OK.")

def run_tests():
    log("yellow", "Ejecutando bateria de tests...")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-v"],
                       capture_output=False, cwd=ROOT)
    if r.returncode == 0:
        log("green", "Tests: TODOS PASARON")
    else:
        log("red", "Tests: FALLOS DETECTADOS (continuando de todas formas)")

def kill_old_servers():
    log("cyan", "Limpiando procesos anteriores...")
    if sys.platform == "win32":
        script = """
        $procs = @(Get-Process -Name python -ErrorAction SilentlyContinue)
        foreach ($p in $procs) {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter ("ProcessId = " + $p.Id)).CommandLine
                if ($cmd -match "uvicorn" -or $cmd -match "http.server") { $p.Kill() }
            } catch {}
        }
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, timeout=10)
    else:
        subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
        subprocess.run(["pkill", "-f", "http.server"], capture_output=True)
    time.sleep(2)

def start_backend():
    global backend_proc
    log("cyan", f"Iniciando backend en puerto {BACKEND_PORT}...")
    logfile = open(os.path.join(ROOT, "logs", "backend.log"), "a")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app",
         "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
        cwd=ROOT, env=env, stdout=logfile, stderr=subprocess.STDOUT
    )
    for i in range(15):
        time.sleep(1)
        try:
            import urllib.request
            r = urllib.request.urlopen(f"http://localhost:{BACKEND_PORT}/api/status", timeout=2)
            if r.status == 200:
                data = json.loads(r.read())
                modules = len(data.get("modules", {}))
                log("green", f"Backend OK ({modules} modulos) -> http://localhost:{BACKEND_PORT}")
                return True
        except Exception:
            pass
    log("red", f"Backend NO RESPONDE. Revise logs/backend.log")
    return False

def start_frontend():
    global frontend_proc
    log("cyan", f"Iniciando frontend en puerto {FRONTEND_PORT}...")
    logfile = open(os.path.join(ROOT, "logs", "frontend.log"), "a")
    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(FRONTEND_PORT)],
        cwd=os.path.join(ROOT, "frontend"), stdout=logfile, stderr=subprocess.STDOUT
    )
    time.sleep(2)
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://localhost:{FRONTEND_PORT}/dashboard.html", timeout=2)
        log("green", f"Frontend OK -> http://localhost:{FRONTEND_PORT}/dashboard.html")
        return True
    except Exception:
        log("red", f"Frontend NO RESPONDE. Revise logs/frontend.log")
        return False

def stop_all():
    global backend_proc, frontend_proc
    log("yellow", "Deteniendo servicios...")
    for p in [backend_proc, frontend_proc]:
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    kill_old_servers()
    log("green", "ZiCore detenido.")

def open_browser():
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}/dashboard.html")

def show_status():
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://localhost:{BACKEND_PORT}/api/status", timeout=3)
        data = json.loads(r.read())
        print(f"\nStatus: {data['status']} | Version: {data['version']}")
        for name, mod in data["modules"].items():
            color = "\033[32m" if mod.get("status") == "nominal" else "\033[33m"
            print(f"  {color}{name}: {mod['status']}\033[0m")
        print()
    except Exception as e:
        log("red", f"Backend no disponible: {e}")

def show_logs():
    for name, path in [("Backend", "logs/backend.log"), ("Frontend", "logs/frontend.log")]:
        print(f"\n-- {name} logs (ultimas 10 lineas) --")
        try:
            with open(os.path.join(ROOT, path)) as f:
                lines = f.readlines()
                for l in lines[-10:]:
                    print(l.rstrip())
        except FileNotFoundError:
            print("  (vacio)")

def run_tests_quick():
    log("yellow", "Ejecutando tests rapidos...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/test_api.py", "-v"],
                   cwd=ROOT)

def signal_handler(sig, frame):
    stop_all()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    # Parse args
    skip_tests = "--skip-tests" in sys.argv or "-s" in sys.argv
    no_browser = "--no-browser" in sys.argv or "-n" in sys.argv
    help_flag = "--help" in sys.argv or "-h" in sys.argv

    if help_flag:
        print("""
ZiCore Mission Control — Startup Script

Sintaxis:  python start.py [--skip-tests] [--no-browser] [--help]

Flags:
  --skip-tests, -s   Salta la bateria de tests inicial
  --no-browser, -n   No abre el navegador automaticamente
  --help, -h         Muestra esta ayuda

Servicios:
  Backend  -> http://localhost:8080  (FastAPI + WebSocket)
  Frontend -> http://localhost:3000  (Dashboard HTML)
  Tests    -> pytest tests/ -v
""")
        return

    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    check_deps()

    if not skip_tests:
        run_tests()

    kill_old_servers()
    backend_ok = start_backend()
    frontend_ok = start_frontend()

    if not no_browser and frontend_ok:
        threading.Thread(target=open_browser, daemon=True).start()

    print()
    log("cyan", "=" * 55)
    log("green", " ZiCore Mission Control — EN LINEA")
    log("cyan", "=" * 55)
    print(f"  Backend  : http://localhost:{BACKEND_PORT}")
    print(f"  Frontend : http://localhost:{FRONTEND_PORT}/dashboard.html")
    print(f"  Logs     : {ROOT}\\logs\\")
    print(f"  Tests    : python -m pytest tests/ -v")
    log("cyan", "=" * 55)
    print()
    print("  Comandos disponibles en esta terminal:")
    print("    status   -> muestra estado de modulos")
    print("    logs     -> muestra ultimas lineas de logs")
    print("    test     -> ejecuta tests rapidos")
    print("    exit     -> detiene todo y sale")
    print()

    try:
        while True:
            cmd = input("zicore> ").strip().lower()
            if cmd == "status":
                show_status()
            elif cmd == "logs":
                show_logs()
            elif cmd == "test":
                run_tests_quick()
            elif cmd == "exit":
                break
            elif cmd:
                print("Comandos: status, logs, test, exit")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        stop_all()

if __name__ == "__main__":
    main()
