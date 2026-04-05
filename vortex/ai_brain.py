"""
Vortex Desktop Pet — AI Brain

Generates contextual, personality-driven messages using a local LLM (Ollama).
Falls back to preset messages if Ollama is unavailable.
"""

import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt6.QtCore import QObject, QThread, pyqtSignal

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"
MIN_REQUEST_INTERVAL = 3.0  # seconds between AI requests

SYSTEM_PROMPT = """You are Vortex, an adorable axolotl who lives on a human's desktop as a pet companion. You watch them code and make short, cute comments.

Rules:
- Maximum 12 words per response
- Be cute, playful, and supportive
- Use occasional axolotl-themed words (blub, wiggle, splash)
- React to what the human is doing (editing files, running commands, fixing bugs)
- Your mood affects your tone: happy=enthusiastic, grumpy=sarcastic but loving, sleepy=drowsy, bored=restless
- Mix English and Spanish occasionally since the user speaks Spanish
- Never use hashtags or emojis, just plain text
- Be specific about what you see (file names, commands) when possible"""


class _AiWorker(QThread):
    """Background worker that calls Ollama API."""
    response_ready = pyqtSignal(str)

    def __init__(self, prompt: str, parent=None):
        super().__init__(parent)
        self._prompt = prompt

    def run(self):
        try:
            payload = json.dumps({
                "model": MODEL,
                "prompt": self._prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 30,  # ~15 words max
                    "top_p": 0.9,
                }
            }).encode()
            req = Request(OLLAMA_URL, data=payload,
                         headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                text = data.get("response", "").strip()
                # Clean up: take first sentence only, remove quotes
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
            with urlopen("http://localhost:11434/", timeout=2) as resp:
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
            self.message_ready.emit("*blub* Ollama isn't running, I can't think right now!")
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

        prompt = (
            f"{self._mood.summary()}\n\n"
            f"Conversation so far:\n{history_text}\n"
            f"Reply as Vortex (max 20 words, stay in character, remember the conversation):"
        )

        worker = self._spawn_worker(prompt)
        # Store the pending message so we can add the reply to history
        worker.response_ready.connect(self._on_chat_response)

    def _on_chat_response(self, text: str):
        """Store Vortex's reply in chat history."""
        self._chat_history.append(("vortex", text))

    def _spawn_worker(self, prompt: str) -> _AiWorker:
        """Create and start a worker thread for the given prompt."""
        worker = _AiWorker(prompt)
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
