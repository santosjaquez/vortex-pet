"""
Vortex Desktop Pet — AI Brain

Generates contextual, personality-driven messages using a local LLM (Ollama).
Falls back to preset messages if Ollama is unavailable.
"""

import base64
import json
import time
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtCore import QObject, QThread, pyqtSignal

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "gemma4:e2b"
# Vision via native model is blocked by Ollama bug #15299
# Using OCR fallback until fixed
MIN_REQUEST_INTERVAL = 3.0  # seconds between AI requests

SYSTEM_PROMPT = """You are Vortex, a sharp and witty AI assistant that lives on a developer's desktop as a compact companion. You observe their workflow and make concise, useful comments.

Rules:
- Maximum 15 words per response
- Be direct, clever, and genuinely helpful — not childish or cutesy
- NO baby talk, NO "blub", "splash", "wiggle", or similar infantile words
- Speak like a smart coworker: dry humor, tech-savvy, occasionally sarcastic
- React specifically to what the developer is doing (file names, commands, errors)
- Your mood affects tone: happy=confident, grumpy=blunt, sleepy=minimal, bored=impatient
- Respond in Spanish if the user writes in Spanish, English if in English
- Never use hashtags or emojis
- Be concise and valuable — if you have nothing useful to say, say something witty instead"""


class _AiWorker(QThread):
    """Background worker that calls Ollama chat API."""
    response_ready = pyqtSignal(str)

    def __init__(self, prompt: str, system: str = None, think: bool = False, parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._system = system or SYSTEM_PROMPT
        self._think = think

    def run(self):
        try:
            # Gemma 4: no system role support, prepend to user message
            full_prompt = f"{self._system}\n\n{self._prompt}"
            messages = [
                {"role": "user", "content": full_prompt},
            ]
            payload = json.dumps({
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "think": self._think,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 200 if self._think else 80,
                    "top_p": 0.9,
                }
            }).encode()
            req = Request(OLLAMA_CHAT_URL, data=payload,
                         headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=120 if self._think else 60) as resp:
                data = json.loads(resp.read())
                msg = data.get("message", {})
                text = msg.get("content", "").strip()
                # If thinking mode and content is empty, extract from thinking
                if not text and self._think:
                    thinking = msg.get("thinking", "")
                    # Get the last paragraph as the answer
                    parts = thinking.strip().split("\n\n")
                    text = parts[-1].strip() if parts else ""
                # Clean up
                if text:
                    text = text.split("\n")[0].strip('" ')
                if text:
                    self.response_ready.emit(text)
        except Exception as e:
            import sys
            print(f"[Vortex AI] Worker error: {e}", file=sys.stderr, flush=True)


class AiBrain(QObject):
    """Generates contextual messages for the desktop pet using local LLM."""

    message_ready = pyqtSignal(str)  # emitted when AI generates a response

    def __init__(self, mood_state, parent=None):
        super().__init__(parent)
        self._mood = mood_state
        self._last_request_time: float = 0
        self._workers: list = []  # keep refs to running workers
        self._chat_history: list[tuple[str, str]] = []  # (role, text) pairs
        self._max_history = 20  # keep last 20 exchanges

    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            with urlopen(OLLAMA_BASE_URL, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_comment(self, context: str):
        """Request an AI-generated comment based on context.

        Args:
            context: Description of what's happening, e.g.
                     "User edited file vortex/app.py using the Edit tool"
        """
        now = time.time()
        if now - self._last_request_time < MIN_REQUEST_INTERVAL:
            return  # rate limited

        if not self._check_ollama():
            return  # Ollama not available, caller should use fallback

        self._last_request_time = now

        prompt = f"{self._mood.summary()}\n\nWhat just happened: {context}\n\nYour short reaction:"
        self._spawn_worker(prompt)

    def generate_chat_reply(self, user_message: str):
        """Generate a reply for the chat window with conversation history.

        Args:
            user_message: What the user typed to Vortex
        """
        now = time.time()
        if not self._check_ollama():
            self.message_ready.emit("Ollama no está corriendo.")
            return

        self._last_request_time = now

        # Add user message to history
        self._chat_history.append(("human", user_message))
        if len(self._chat_history) > self._max_history:
            self._chat_history = self._chat_history[-self._max_history:]

        # Build prompt with conversation history
        history_text = ""
        for role, text in self._chat_history:
            if role == "human":
                history_text += f"Human: {text}\n"
            else:
                history_text += f"Vortex: {text}\n"

        # Detect if user wants deep thinking
        _THINK_KEYWORDS = ["piensa", "think", "analiza", "analyze", "razona",
                           "reason", "explica detallado", "think hard", "piensalo bien"]
        use_think = any(kw in user_message.lower() for kw in _THINK_KEYWORDS)

        max_words = "50 words" if use_think else "20 words"
        prompt = (
            f"{self._mood.summary()}\n\n"
            f"Conversation so far:\n{history_text}\n"
            f"Reply as Vortex (max {max_words}, stay in character, remember the conversation):"
        )

        worker = self._spawn_worker(prompt, think=use_think)
        worker.response_ready.connect(self._on_chat_response)

    def _on_chat_response(self, text: str):
        """Store Vortex's reply in chat history."""
        self._chat_history.append(("vortex", text))

    def analyze_screen(self, user_question: str = ""):
        """Take a screenshot, OCR it, and analyze with text LLM.

        Args:
            user_question: Optional question about what's on screen.
        """
        if not self._check_ollama():
            self.message_ready.emit("Ollama isn't running.")
            return

        # Take screenshot using PyQt6
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen is None:
            self.message_ready.emit("Can't capture screen.")
            return

        pixmap = screen.grabWindow(0)

        # Save to temp file for OCR
        import os
        tmp_path = "/tmp/vortex_screen_ocr.png"
        pixmap.save(tmp_path, "PNG")

        # Run tesseract OCR
        import subprocess
        try:
            result = subprocess.run(
                ["tesseract", tmp_path, "-", "-l", "spa+eng"],
                capture_output=True, text=True, timeout=10
            )
            screen_text = result.stdout.strip()[:2000]  # limit to 2000 chars
        except Exception:
            screen_text = "(could not read screen)"
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Add to history
        self._chat_history.append(("human", f"[Looking at screen] {user_question}"))

        # Build prompt with screen content
        question = user_question if user_question else "What do you see on my screen?"
        prompt = (
            f"{self._mood.summary()}\n\n"
            f"Conversation so far:\n"
            + "".join(f"{'Human' if r=='human' else 'Vortex'}: {t}\n"
                      for r, t in self._chat_history) +
            f"\nThe user asked you to look at their screen. "
            f"Here is the text visible on screen (extracted via OCR):\n"
            f"---\n{screen_text}\n---\n\n"
            f"User's question: {question}\n"
            f"Respond helpfully in 2-3 sentences based on what you can see. "
            f"Use the same language as the question."
        )

        worker = self._spawn_worker(prompt)
        worker.response_ready.connect(self._on_chat_response)

    def _spawn_worker(self, prompt: str, think: bool = False) -> _AiWorker:
        """Create and start a worker thread for the given prompt."""
        worker = _AiWorker(prompt, think=think)
        worker.response_ready.connect(self._on_response)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()
        return worker

    def _cleanup_worker(self, worker):
        """Remove finished worker from the list."""
        try:
            self._workers.remove(worker)
        except ValueError:
            pass
        worker.deleteLater()

    def _on_response(self, text: str):
        """Handle AI response from worker thread."""
        self.message_ready.emit(text)

    def build_tool_context(self, event_name: str, data: dict) -> str:
        """Build a context string from a Claude Code hook event."""
        tool = data.get("tool_name", "unknown")
        tool_input = data.get("tool_input", {})

        if event_name == "PostToolUse":
            if tool == "Bash":
                cmd = str(tool_input.get("command", ""))[:80]
                return f"User ran a bash command: {cmd}"
            elif tool == "Edit":
                file_path = str(tool_input.get("file_path", ""))
                # Only keep filename, not full path
                filename = file_path.split("/")[-1] if "/" in file_path else file_path
                return f"User edited file: {filename}"
            elif tool == "Write":
                file_path = str(tool_input.get("file_path", ""))
                filename = file_path.split("/")[-1] if "/" in file_path else file_path
                return f"User created/wrote file: {filename}"
            elif tool == "Read":
                file_path = str(tool_input.get("file_path", ""))
                filename = file_path.split("/")[-1] if "/" in file_path else file_path
                return f"User is reading file: {filename}"
            elif tool in ("Grep", "Glob"):
                pattern = str(tool_input.get("pattern", ""))[:50]
                return f"User searched for: {pattern}"
            else:
                return f"User used tool: {tool}"
        elif event_name == "PostToolUseFailure":
            return f"A tool failed: {tool}. Something went wrong."
        elif event_name == "Stop":
            return "Claude finished responding. The task might be done."
        elif event_name == "Notification":
            return "A notification was sent to the user."
        elif event_name == "SessionStart":
            return "A new coding session just started!"
        elif event_name == "SessionEnd":
            return "The coding session ended."
        else:
            return f"Event: {event_name}"
