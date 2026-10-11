"""One text-in, text-out model call for the parser, with the trace entry the event requires.

Backends, tried in this order (standard library only, nothing to install); a backend that fails hands the call to the next:
  1. Anthropic Messages API over HTTPS when ANTHROPIC_API_KEY is set.
  2. The `claude` CLI in print mode (uses the machine's Claude login), tools disabled.
If every backend fails on the requested model, the call is tried once more on FALLBACK_MODEL (a refused or
rate-limited model must not cost the whole build). Every call is logged with `trace.model_call(model, purpose)`.
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
FALLBACK_MODEL = os.environ.get("PARSER_FALLBACK_MODEL", "claude-sonnet-5-5")   # empty string: no fallback model
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
           "--no-session-persistence", "--system-prompt",
           "You are a precise component of a software pipeline. Follow the instructions in the user message and answer exactly in the format they ask for."]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    with tempfile.TemporaryDirectory() as cwd:   # empty cwd: no project memory or settings leak into the call
        # the long instructions go through stdin: a Windows command line is limited to about 32k characters
        stdin = "<instructions>" + chr(10) + system + chr(10) + "</instructions>" + chr(10) * 2 + prompt
        p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace",
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


def _replay(purpose, system, prompt):
    """Development aid: with PARSER_REPLAY_DIR set, prompts are written there and answers are read from <slug>.answer.txt."""
    import pathlib, re
    d = pathlib.Path(os.environ["PARSER_REPLAY_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"\W+", "_", purpose)[:60]
    (d / "system.txt").write_text(system, encoding="utf-8")
    (d / f"{slug}.prompt.txt").write_text(prompt, encoding="utf-8")
    ans = d / f"{slug}.answer.txt"
    if not ans.exists():
        raise RuntimeError(f"replay: no answer file {ans.name}")
    return ans.read_text(encoding="utf-8")


def complete(purpose, system, prompt, model=None, max_tokens=24000, timeout=420):
    """Return the model's text. Raises on failure (the caller decides whether to retry)."""
    model = model or DEFAULT_MODEL
    if os.environ.get("PARSER_REPLAY_DIR"):
        return _replay(purpose, system, prompt)
    t0 = time.time()
    order = (["api"] if os.environ.get("ANTHROPIC_API_KEY") else []) + (["cli"] if (shutil.which("claude") or shutil.which("claude.cmd")) else [])
    order = order or ["cli"]                       # nothing available: the CLI call raises the clear "cannot call a model" error
    text, err = None, None
    for m in [model] + ([FALLBACK_MODEL] if FALLBACK_MODEL and FALLBACK_MODEL != model else []):
        if m != model and trace is not None:
            trace.note(f"model {model} failed on every backend; retrying on fallback model {m}")
        for backend in order:                      # a failing backend (bad key, usage limit) falls back to the other one
            _log(m, purpose, backend=backend, prompt_chars=len(prompt))
            try:
                text = _call_api(m, system, prompt, max_tokens, timeout) if backend == "api" else _call_cli(m, system, prompt, timeout)
                break
            except Exception as e:  # noqa: BLE001
                err = e
                if trace is not None:
                    trace.note(f"model call failed on backend {backend}: {str(e)[:300]}")
        if text is not None:
            break
    if text is None:
        raise err
    if trace is not None:
        trace.note(f"model call done in {time.time() - t0:.0f}s: {purpose} ({len(text)} chars)")
    return text


def extract_json(text):
    """The JSON object in a model answer: a fenced block first, else the first object that decodes, whatever text
    surrounds it (a brace in the commentary, a bracketed note before it). Two different objects in one answer are
    ambiguous (one may be a correction), so that raises and the caller's retry path runs."""
    s = text.strip()
    if "```" in s:
        for part in s.split("```")[1::2]:
            part = part[4:] if part.startswith("json") else part
            if part.strip().startswith(("{", "[")):
                s = part.strip()
                break
    dec = json.JSONDecoder()
    found, i = [], 0
    while True:
        i = s.find("{", i)
        if i < 0:
            break
        try:
            obj, end = dec.raw_decode(s, i)
        except ValueError:
            i += 1
            continue
        if isinstance(obj, dict):
            found.append(obj)
            if len(found) > 1 and found[1] != found[0]:
                break
        i = end
    if not found:
        start = s.find("[")
        if start < 0:
            raise ValueError("no JSON in model answer")
        return dec.raw_decode(s, start)[0]          # an answer that is a bare array
    if len(found) > 1 and found[1] != found[0]:
        raise ValueError("ambiguous model answer: more than one JSON object")
    return found[0]
