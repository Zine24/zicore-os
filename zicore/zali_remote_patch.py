"""ZIO Agent V2 — Multimodal Agent Loop (Recursive)
Perceive -> Interpret -> Reason -> Decide -> Execute -> Observe -> Decide again...

NOW RECURSIVE: after each LLM call, if tool results exist or the model
requests further processing, the loop feeds results back to the LLM
for up to MAX_ROUNDS iterations.

This makes ZIO think in chains: reason → act → observe → reason → act → ...
Until it produces a final answer with no pending tool calls.
"""
import re
import logging
import time
from core.agent_router import AgentRouter, Intent
from core.tool_router import ToolRouter
from core.job_manager import JobManager
from core.session import Session, Message

log = logging.getLogger("zio-agent.multimodal")

CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

MAX_ROUNDS = 5


def _extract_code_blocks(text: str) -> list[str]:
    """Extract fenced code blocks from markdown text."""
    blocks = CODE_BLOCK_RE.findall(text)
    return [b.strip() for b in blocks if b.strip()]


class MultimodalAgent:
    def __init__(self, router: AgentRouter, tools: ToolRouter, jobs: JobManager,
                 llm_pipeline=None, vision_pipeline=None, speech_pipeline=None,
                 tts_pipeline=None, embedding_pipeline=None, memory_client=None):
        self.router = router
        self.tools = tools
        self.jobs = jobs
        self.llm = llm_pipeline
        self.vision = vision_pipeline
        self.speech = speech_pipeline
        self.tts = tts_pipeline
        self.embedding = embedding_pipeline
        self.memory = memory_client

    async def process(self, session: Session, text: str = "",
                      image_data: str = None, audio_data: str = None,
                      system_prompt: str = "") -> dict:
        start = time.time()
        has_image = image_data is not None
        has_audio = audio_data is not None

        session.add_message("user", text, images=[image_data] if has_image else [],
                           audio=[audio_data] if has_audio else [])

        intent = self.router.classify(text, has_image=has_image, has_audio=has_audio)
        log.info(f"Intent: {intent.category}/{intent.action} (conf={intent.confidence:.2f})")

        # Preprocess: vision
        if has_image and self.vision:
            vision_result = await self.vision.analyze_image(image_data, model="gemma3:1b")
            image_context = vision_result.get("description", "")
            if image_context:
                text = f"[Image analysis: {image_context}]\n\nUser message: {text}"

        # Preprocess: speech
        if has_audio and self.speech:
            stt_result = await self.speech.transcribe(audio_data=audio_data)
            transcribed = stt_result.get("text", "")
            if transcribed:
                text = f"[Transcribed audio: {transcribed}]\n\nUser message: {text}"

        # Preprocess: memory
        if intent.category == "memory" and self.memory:
            if intent.action == "search" and self.embedding:
                query_vec = await self.embedding.embed_text(text)
                if query_vec:
                    results = await self.memory.search(query_vec, limit=5)
                    if results:
                        context = "\n".join(r.get("text", "") for r in results)
                        text = f"[Relevant context from memory:\n{context}]\n\nUser: {text}"

        # --- EXECUTE tools before LLM for file read/list operations ---
        tool_results = []
        if intent.category == "file" and intent.action in ("read", "list"):
            file_result = await self._execute_file_intent(intent, text)
            if file_result:
                tool_results.append(file_result)
                file_content = file_result.get("result", {})
                if isinstance(file_content, dict) and "content" in file_content:
                    text = f"[File content of {file_content.get('path', 'file')}:\n{file_content['content'][:8000]}]\n\nUser: {text}"
                elif isinstance(file_content, dict) and "entries" in file_content:
                    entries_str = "\n".join(
                        f"  {'[DIR] ' if e['type']=='dir' else ''}{e['name']} ({e.get('size',0)} bytes)"
                        for e in file_content["entries"]
                    )
                    text = f"[Directory listing of {file_content.get('path', 'dir')}:\n{entries_str}]\n\nUser: {text}"
                elif isinstance(file_content, dict) and "error" in file_content:
                    text = f"[File error: {file_content['error']}]\n\nUser: {text}"

        # --- RECURSIVE LLM LOOP ---
        # Keep calling LLM with accumulated context until:
        # - No more tool results to process
        # - Model produces final answer
        # - MAX_ROUNDS reached
        response_text = ""
        rounds = 0
        pending_tool_results = list(tool_results)

        while rounds < MAX_ROUNDS:
            rounds += 1

            if self.llm:
                history = session.get_history(limit=10)
                messages = [{"role": "system", "content": system_prompt or self._default_system()}]
                for h in history[:-1]:
                    messages.append({"role": h["role"], "content": h["content"]})

                # Build the user message with accumulated tool context
                user_content = text
                if pending_tool_results:
                    tool_summary = "\n".join(
                        f"[Tool: {tr.get('tool', 'unknown')}] {tr.get('result', '')}"
                        if isinstance(tr, dict) else str(tr)
                        for tr in pending_tool_results
                    )
                    user_content = f"{text}\n\n--- TOOL RESULTS (round {rounds}) ---\n{tool_summary}\n--- END TOOLS ---\nAnalyze these results and continue your reasoning."

                messages.append({"role": "user", "content": user_content})

                llm_result = await self.llm.chat(messages, images=[image_data] if has_image else None)
                response_text = llm_result.get("response", "")
                if llm_result.get("error"):
                    log.warning(f"LLM error round {rounds}: {llm_result['error']}")
                    break
            else:
                response_text = f"Processed ({intent.category}/{intent.action}). LLM not available."
                break

            # --- AUTO-EXECUTE code blocks for code intent ---
            if intent.category == "code" and intent.action == "execute":
                code_blocks = _extract_code_blocks(response_text)
                if not code_blocks and text:
                    user_code = self._extract_inline_code(text)
                    if user_code:
                        code_blocks = [user_code]

                if code_blocks:
                    log.info(f"Round {rounds}: auto-executing {len(code_blocks)} code block(s)")
                    new_results = []
                    for i, block in enumerate(code_blocks):
                        exec_result = await self._execute_code_block(block)
                        new_results.append(exec_result)
                        result_data = exec_result.get("result", {})
                        if isinstance(result_data, dict):
                            stdout = result_data.get("stdout", "")
                            stderr = result_data.get("stderr", "")
                            exit_code = result_data.get("exit_code", -1)
                            exec_time = result_data.get("execution_time_s", 0)
                            success = result_data.get("success", False)

                            if success and stdout:
                                response_text += f"\n\n**Output (block {i+1}):**\n```\n{stdout[:3000]}\n```"
                            elif not success and stderr:
                                response_text += f"\n\n**Error (block {i+1}):**\n```\n{stderr[:2000]}\n```"
                            elif not success and not stderr:
                                response_text += f"\n\n**Exit code: {exit_code}** (no output, {exec_time}s)"
                            if exec_time > 0:
                                response_text += f"\n*[{exec_time}s]*"

                    # Check if results need further reasoning
                    has_output = any(
                        isinstance(r.get("result"), dict) and r["result"].get("stdout", "")
                        for r in new_results
                    )
                    if has_output and rounds < MAX_ROUNDS:
                        pending_tool_results = new_results
                        # Continue loop — LLM will analyze the output
                        session.add_message("assistant", f"[Code executed, analyzing output...]")
                        continue
                    break

            # --- AUTO-EXECUTE file write/edit/delete ---
            if intent.category == "file" and intent.action in ("write", "edit", "delete"):
                file_result = await self._execute_file_intent(intent, text)
                if file_result:
                    tool_results.append(file_result)
                    result_data = file_result.get("result", {})
                    if isinstance(result_data, dict):
                        if result_data.get("success"):
                            path = result_data.get("path", "")
                            if intent.action == "write":
                                response_text += f"\n\n**File written:** `{path}` ({result_data.get('bytes_written', 0)} bytes)"
                            elif intent.action == "edit":
                                response_text += f"\n\n**File edited:** `{path}` ({result_data.get('occurrences', 0)} occurrence(s) replaced)"
                            elif intent.action == "delete":
                                response_text += f"\n\n**File deleted:** `{path}`"
                        elif "error" in result_data:
                            response_text += f"\n\n**File error:** {result_data['error']}"

            # No more pending results — exit loop
            pending_tool_results = []
            break

        log.info(f"Agent completed in {rounds} round(s)")

        # --- Store in session ---
        session.add_message("assistant", response_text, metadata={
            "intent": intent.category,
            "action": intent.action,
            "rounds": rounds,
            "tool_results": tool_results if tool_results else None,
        })

        # --- Memory correction ---
        if self.memory and self.embedding:
            try:
                vec = await self.embedding.embed_text(response_text)
                if vec:
                    await self.memory.store(vec, response_text, metadata={
                        "session_id": session.session_id,
                        "intent": intent.category,
                        "rounds": rounds,
                    })
            except Exception as e:
                log.warning(f"Memory store failed: {e}")

        elapsed = round(time.time() - start, 2)
        return {
            "response": response_text,
            "intent": {"category": intent.category, "action": intent.action, "confidence": intent.confidence},
            "elapsed_s": elapsed,
            "rounds": rounds,
            "session_id": session.session_id,
            "tool_results": tool_results if tool_results else None,
        }

    async def _execute_code_block(self, code: str) -> dict:
        """Execute a single code block via the code_execute tool."""
        try:
            result = await self.tools.execute("code_execute", code=code, timeout=30)
            return result
        except Exception as e:
            log.error(f"Code execution failed: {e}")
            return {"status": "error", "tool": "code_execute", "error": str(e)}

    async def _execute_file_intent(self, intent: Intent, text: str) -> dict:
        """Parse and execute a file operation from the user's message."""
        try:
            action = intent.action
            path = self._extract_path(text)
            content = self._extract_content(text)
            old_text = ""
            new_text = ""
            if action == "edit":
                old_text, new_text = self._extract_edit_parts(text)

            kwargs = {"action": action}
            if path:
                kwargs["path"] = path
            if content:
                kwargs["content"] = content
            if old_text:
                kwargs["old_text"] = old_text
            if new_text:
                kwargs["new_text"] = new_text
            if action == "list" and not path:
                kwargs["path"] = "/tmp/zio_sandbox"
            kwargs["create_dirs"] = True

            result = await self.tools.execute("file_edit", **kwargs)
            return result
        except Exception as e:
            log.error(f"File intent execution failed: {e}")
            return {"status": "error", "tool": "file_edit", "error": str(e)}

    def _extract_inline_code(self, text: str) -> str:
        blocks = _extract_code_blocks(text)
        if blocks:
            return blocks[0]
        m = INLINE_CODE_RE.search(text)
        if m:
            candidate = m.group(1).strip()
            if any(kw in candidate for kw in ("import ", "print(", "def ", "class ", "for ", "while ", "return ")):
                return candidate
        stripped = text.strip()
        py_keywords = ["import ", "print(", "def ", "class ", "for ", "while ", "if ", "return ", "range("]
        has_py = sum(1 for kw in py_keywords if kw in stripped)
        natural_words = len(re.findall(r'\b(the|a|an|is|are|was|were|to|from|with|and|or|not|that|this)\b', stripped.lower()))
        if has_py >= 2 and natural_words < 3:
            return stripped
        return ""

    def _extract_path(self, text: str) -> str:
        patterns = [
            r"(?:read|cat|show|open|write|save|edit|modify|delete|remove)\s+(?:to\s+|from\s+)?[`\"']?([/~][\w./\-_.]+)",
            r"(?:in|at|to|from)\s+[`\"']?([/][\w./\-_.]+)",
            r"[`\"']([/][\w./\-_.]+)[`\"']",
            r"[`\"']([\w./\-_.]+\.\w+)[`\"']",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return ""

    def _extract_content(self, text: str) -> str:
        blocks = _extract_code_blocks(text)
        if blocks:
            return blocks[0]
        m = re.search(r'[\""]([^\""]{2,})[\""]', text)
        if m:
            return m.group(1)
        return ""

    def _extract_edit_parts(self, text: str) -> tuple[str, str]:
        m = re.search(r'replace\s+["\'](.+?)["\']\s+with\s+["\'](.+?)["\']', text, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r'["\'](.+?)["\']\s*(?:->|=>|→|to)\s*["\'](.+?)["\']', text, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r'from\s+["\'](.+?)["\']\s+to\s+["\'](.+?)["\']', text, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
        return "", ""

    def _default_system(self) -> str:
        return """You are ZIO Agent V2 — a multimodal agentic AI for ZiAerospace.
You can see images, hear audio, generate 3D models, process media, search the web, and execute code.
When the user asks you to write code, write it in fenced Python code blocks (```python ... ```).
When the user asks about files, help them read, write, or edit files.
Always think step by step. Use tools when needed. Be concise and professional.
You are part of the ZICORE aerospace operating system ecosystem.
You have a RECURSIVE reasoning loop: after executing tools, you will see the results
and can reason about them further. Give your best final answer when done."""
