"""One text-in, text-out model call for the parser, with the trace entry the event requires.

Backends, tried in this order (standard library only, nothing to install):
  1. Anthropic Messages API over HTTPS when ANTHROPIC_API_KEY is set.
  2. The `claude` CLI in print mode (uses the machine's Claude login), tools disabled.
Every call is logged with `trace.model_call(model, purpose)`.
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

try:
    from builder import trace
except ImportError:  # standalone use
    trace = None

DEFAULT_MODEL = os.environ.get("PARSER_MODEL", "claude-opus-5-5")
API_URL = "https://api.anthropic.com/v1/messages"


def _log(model, purpose, **info):
    if trace is not None:
        trace.model_call(model, purpose, **info)


def _call_api(model, system, prompt, max_tokens, timeout):
    body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json", "anthropic-version": "2023-06-01",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Anthropic API {e.code}: {e.read()[:500].decode('utf-8', 'replace')}") from None
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _call_cli(model, system, prompt, timeout):
    exe = shutil.which("claude") or shutil.which("claude.cmd")
    if not exe:
        raise RuntimeError("no ANTHROPIC_API_KEY and no `claude` CLI on PATH: cannot call a model")
    cmd = [exe, "-p", "--model", model, "--output-format", "json", "--tools", "",
           "--no-session-persistence", "--system-prompt", system]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    with tempfile.TemporaryDirectory() as cwd:   # empty cwd: no project memory or settings leak into the call
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, cwd=cwd, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"claude CLI failed ({p.returncode}): {(p.stderr or p.stdout)[:500]}")
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        return p.stdout
    if out.get("is_error"):
        raise RuntimeError(f"claude CLI error: {str(out.get('result'))[:500]}")
    return out.get("result", "")


def complete(purpose, system, prompt, model=None, max_tokens=24000, timeout=420):
    """Return the model's text. Raises on failure (the caller decides whether to retry)."""
    model = model or DEFAULT_MODEL
    t0 = time.time()
    backend = "api" if os.environ.get("ANTHROPIC_API_KEY") else "cli"
    _log(model, purpose, backend=backend, prompt_chars=len(prompt))
    text = _call_api(model, system, prompt, max_tokens, timeout) if backend == "api" else _call_cli(model, system, prompt, timeout)
    if trace is not None:
        trace.note(f"model call done in {time.time() - t0:.0f}s: {purpose} ({len(text)} chars)")
    return text


def extract_json(text):
    """Pull the outermost JSON object out of a model answer (fenced or not)."""
    s = text.strip()
    if "```" in s:
        parts = s.split("```")
        for part in parts[1::2]:
            part = part[4:] if part.startswith("json") else part
            if part.strip().startswith(("{", "[")):
                s = part.strip()
                break
    start = min([i for i in (s.find("{"), s.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON in model answer")
    end = max(s.rfind("}"), s.rfind("]"))
    return json.loads(s[start:end + 1])
