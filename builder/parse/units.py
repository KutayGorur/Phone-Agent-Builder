"""Split brief files into addressable units so every piece of a brief can be cited and audited.

A unit is one numbered rule (with its nested bullets), one table, or one paragraph.
Unit ids: the rule number for numbered rules ("39"), "t<k>" for tables, "p<k>" for paragraphs.
With several brief files the ids get a file tag ("a:39", "b:t1"); the tag is the letter after "brief-"
in the file name, else the file stem. File order is precedence order: later files override earlier ones.
Nothing here is specific to any brief: it only looks at markdown structure.
"""
import pathlib
import re

NUM_RE = re.compile(r"^\s{0,3}(?:(\d+(?:\.\d+)+)[.)]?|(\d+)[.)])\s+(.*)$")   # "12. text", "9.4 text"
ITEM_RE = re.compile(r"^(?:\(?([a-zA-Z])[).]|[-*•])\s+(.*)$")      # "a) text", "- text" at the left margin
RULER_RE = re.compile(r"^\s*([-_=*]\s*){3,}$")                    # "-----", "====": a separator, not a unit


def file_tag(path):
    stem = pathlib.Path(path).stem
    m = re.match(r"brief[-_ ]?([A-Za-z0-9]+)$", stem, re.I)
    return (m.group(1) if m else stem).lower()


def split_units(text, tag=None):
    """Return a list of dicts: id, kind (rule|table|paragraph), section, text."""
    prefix = f"{tag}:" if tag else ""
    units, section = [], ""
    cur = None            # unit being built
    counters = {"p": 0, "t": 0, "i": 0, "parent": None}

    def flush():
        nonlocal cur
        if cur:
            cur["text"] = "\n".join(cur["lines"]).strip()
            del cur["lines"]
            if cur["text"]:
                units.append(cur)
        cur = None

    def start(kind, uid, line):
        nonlocal cur
        flush()
        cur = {"id": prefix + uid, "kind": kind, "section": section, "lines": [line]}

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            section = stripped.lstrip("#").strip()
            continue
        if RULER_RE.match(line) and not stripped.startswith("|"):
            if cur and cur["kind"] != "rule":
                flush()
            continue
        if not stripped:
            if cur and cur["kind"] != "rule":
                flush()
            elif cur:
                cur["lines"].append("")
            continue
        m = NUM_RE.match(line)
        if m and not line.startswith("    "):
            start("rule", m.group(1) or m.group(2), line.strip())
            continue
        if stripped.startswith("|"):
            if cur and cur["kind"] == "table":
                cur["lines"].append(stripped)
            else:
                counters["t"] += 1
                start("table", f"t{counters['t']}", stripped)
            continue
        mi = ITEM_RE.match(line) if not line.startswith((" ", "	")) else None
        if mi and not (cur and cur["kind"] == "rule" and cur["lines"] and cur["lines"][-1] != ""):
            parent = f"p{counters['p']}"
            counters["i"] = counters["i"] + 1 if counters.get("parent") == parent else 1
            counters["parent"] = parent
            label = mi.group(1) or str(counters["i"])
            start("item", f"{parent}.{label}", stripped)
            continue
        if cur and cur["kind"] == "rule":
            # continuation / nested bullet of a rule, unless it is a flush-left paragraph after a blank line
            if cur["lines"] and cur["lines"][-1] == "" and not line.startswith((" ", "\t")):
                flush()
            else:
                cur["lines"].append(line.rstrip())
                continue
        if cur and cur["kind"] in ("paragraph", "item"):
            cur["lines"].append(stripped)
            continue
        counters["p"] += 1
        start("paragraph", f"p{counters['p']}", stripped)
    flush()
    return units


def load_briefs(paths):
    """Read brief files in precedence order and return (units, sources) with file tags when there are several."""
    paths = [pathlib.Path(p) for p in paths]
    multi = len(paths) > 1
    units, sources = [], []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        tag = file_tag(p) if multi else None
        sources.append({"file": p.name, "tag": tag})
        for u in split_units(text, tag):
            u["file"] = p.name
            units.append(u)
    return units, sources


def render_units(units):
    """Text form handed to the model: one block per unit, id first."""
    out, last_file, last_section = [], None, None
    for u in units:
        if u["file"] != last_file:
            out.append(f"\n=== FILE {u['file']} ===")
            last_file, last_section = u["file"], None
        if u["section"] != last_section:
            out.append(f"\n## {u['section']}")
            last_section = u["section"]
        out.append(f"[{u['id']}] {u['text']}")
    return "\n".join(out).strip()


if __name__ == "__main__":
    import sys
    us, _ = load_briefs(sys.argv[1:])
    for u in us:
        print(u["id"], u["kind"], "|", u["section"], "|", u["text"][:70].replace("\n", " / "))
