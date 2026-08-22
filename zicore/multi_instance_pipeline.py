"""
ZICORE Multi-Instance Pipeline
Uses gemma3:270m as orchestrator + 3 parallel workers on .68 Ollama via Tailscale.
Each worker gets a fresh context (no degradation from long conversations).
"""
import json
import os
import time
import urllib.request
import concurrent.futures
from typing import Dict, List, Optional

OLLAMA_URL = os.environ.get("ZICORE_OLLAMA_BASE_URL", "http://100.94.98.59:11434")
ORCHESTRATOR_MODEL = "gemma3:270m"
WORKER_MODEL = "gemma3:270m"


def _ollama_generate(model: str, prompt: str, system: str = "",
                     num_predict: int = 800, temperature: float = 0.7,
                     timeout: int = 120) -> str:
    """Single Ollama generation call"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": 4096,
        }
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"


def decompose_task(user_message: str) -> List[Dict]:
    """Use orchestrator to decompose a task into subtasks"""
    system = """You are ZIO, the ZICORE Intelligence Operator task orchestrator.
Your job is to analyze the user's request and break it into 2-4 independent subtasks.

Return ONLY a JSON array like:
[{"id": 1, "task": "description of subtask", "role": "analyst|coder|reviewer"}]

Roles:
- analyst: analyze, research, explain
- coder: write code, generate implementations
- reviewer: review, test, validate, document

Be concise. Return ONLY the JSON array, no other text."""

    response = _ollama_generate(ORCHESTRATOR_MODEL, user_message, system,
                                num_predict=500, temperature=0.3)

    # Parse JSON from response
    try:
        # Find JSON array in response
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass

    # Fallback: single task
    return [{"id": 1, "task": user_message, "role": "coder"}]


def execute_subtask(subtask: Dict, user_context: str) -> Dict:
    """Execute a single subtask with a fresh worker instance"""
    role = subtask.get("role", "coder")
    task = subtask.get("task", "")

    role_prompts = {
        "analyst": "You are an expert analyst. Analyze the following task thoroughly and provide clear insights.",
        "coder": "You are an expert programmer. Write clean, efficient code for the following task.",
        "reviewer": "You are an expert code reviewer. Review, validate, and document the following."
    }

    system = role_prompts.get(role, role_prompts["coder"])
    prompt = f"User request: {user_context}\n\nYour specific task: {task}"

    start = time.time()
    result = _ollama_generate(WORKER_MODEL, prompt, system,
                              num_predict=800, temperature=0.7)
    elapsed = time.time() - start

    return {
        "id": subtask.get("id", 0),
        "role": role,
        "task": task,
        "result": result,
        "time": round(elapsed, 2)
    }


def integrate_results(user_message: str, subtask_results: List[Dict]) -> str:
    """Use orchestrator to integrate subtask results into final response"""
    results_text = "\n\n".join([
        f"## Subtask {r['id']} ({r['role']}) [{r['time']}s]\n{r['result']}"
        for r in subtask_results
    ])

    system = """You are ZIO, the ZICORE Intelligence Operator.
You have received results from multiple workers who completed subtasks.
Integrate these results into a single, coherent, helpful response for the user.
Be concise but thorough. Remove redundancies."""

    prompt = f"Original user request: {user_message}\n\nWorker results:\n{results_text}"

    return _ollama_generate(ORCHESTRATOR_MODEL, prompt, system,
                            num_predict=1000, temperature=0.5)


def run_pipeline(user_message: str, max_workers: int = 3) -> Dict:
    """Run the full multi-instance pipeline"""
    start_total = time.time()

    # Step 1: Decompose
    t0 = time.time()
    subtasks = decompose_task(user_message)
    decompose_time = time.time() - t0

    # Step 2: Execute subtasks in parallel (limited to max_workers)
    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(execute_subtask, st, user_message): st
            for st in subtasks[:max_workers]
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda x: x["id"])
    execute_time = time.time() - t0

    # Step 3: Integrate
    t0 = time.time()
    final_response = integrate_results(user_message, results)
    integrate_time = time.time() - t0

    total_time = time.time() - start_total

    return {
        "response": final_response,
        "pipeline": {
            "subtasks": len(subtasks),
            "decompose_time": round(decompose_time, 2),
            "execute_time": round(execute_time, 2),
            "integrate_time": round(integrate_time, 2),
            "total_time": round(total_time, 2),
            "worker_results": [{
                "id": r["id"],
                "role": r["role"],
                "time": r["time"],
                "result_length": len(r["result"])
            } for r in results]
        }
    }
