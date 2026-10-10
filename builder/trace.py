"""Plain-text trace of one builder run, written to a file and echoed to stdout.

Records: start and end time, every model call (model + one-line purpose), every Freya resource created or
updated, every self-test with its result. Secrets are redacted from every line.

Other modules (parser, generator, fixer) record their model calls with
    from builder import trace
    trace.model_call("claude-opus-5-5", "parse brief into spec.json")
"""
import os, pathlib, re, threading, time

_SECRET_ENV = ("FREYA_API_KEY", "FREYA_BANK_TEAM_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")
_PATTERNS = [re.compile(p) for p in (r"fak_[A-Za-z0-9_\-]+", r"sk-ant-[A-Za-z0-9_\-]+", r"sk-[A-Za-z0-9_\-]{20,}", r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}")]


def redact(text):
    text = str(text)
    for name in _SECRET_ENV:
        v = os.environ.get(name)
        if v and len(v) >= 8:
            text = text.replace(v, "[REDACTED]")
    for p in _PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text


class Trace:
    def __init__(self, path=None, echo=True):
        self.path = pathlib.Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.echo, self.t0, self.lock = echo, time.time(), threading.Lock()
        self.model_calls = 0

    def _line(self, tag, msg):
        line = redact(f"{time.strftime('%Y-%m-%d %H:%M:%S')} +{time.time() - self.t0:6.0f}s [{tag}] " + " ".join(str(msg).split()))
        with self.lock:
            if self.path:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            if self.echo:
                print(line, flush=True)

    def start(self, **info):
        self._line("START", " ".join(f"{k}={v}" for k, v in info.items()))

    def end(self, status, **info):
        self._line("END", f"status={status} elapsed={time.time() - self.t0:.0f}s model_calls={self.model_calls} " + " ".join(f"{k}={v}" for k, v in info.items()))

    def note(self, msg): self._line("INFO", msg)
    def stage(self, name): self._line("STAGE", name)
    def error(self, msg): self._line("ERROR", msg)
    def freya(self, action, **info): self._line("FREYA", f"{action} " + " ".join(f"{k}={v}" for k, v in info.items()))
    def selftest(self, msg): self._line("SELFTEST", msg)

    def model_call(self, model, purpose, **info):
        self.model_calls += 1
        self._line("MODEL", f"model={model} purpose={purpose} " + " ".join(f"{k}={v}" for k, v in info.items()))


_current = Trace(echo=False)   # replaced by build.py; keeps imports safe when used standalone


def set_current(t):
    global _current
    _current = t


def get(): return _current
def model_call(model, purpose, **info): _current.model_call(model, purpose, **info)
def note(msg): _current.note(msg)
