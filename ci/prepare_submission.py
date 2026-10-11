"""Collect each brief's workflow export and trace into a committed folder and print the submission form fields.

python3 ci/prepare_submission.py hidden-1 hidden-2            # dry run (default): checks and prints, copies nothing
python3 ci/prepare_submission.py hidden-1 hidden-2 --apply    # copy into submission/ and `git add -f`
python3 ci/prepare_submission.py hidden-1 --apply --commit    # also commit (never pushes, never deletes)
A stem is the builder's output name: out/<stem>.workflow.json (the freya.export_workflow file) and the newest
traces/<stem>-*.trace.txt. Multi-file builds use the joined stem, e.g. brief-a-brief-b.
Files: submission/<stem>.workflow.json and submission/traces/<stem>.log. Run only after the final builds; do not edit afterwards.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from builder import trace as trace_mod

RUN_CMD = "python3 builder/build.py {brief_path} {tool_api_path} 2>&1 | tee traces/{stem}.log"


def git(*a, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=check).stdout.strip()


def newest_trace(traces_dir, stem):
    c = [p for p in traces_dir.glob(f"{stem}-*.trace.txt") if re.fullmatch(r"\d[\d\-_T:.]*", p.name[len(stem) + 1:-len(".trace.txt")])]
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


def check(stem, wf, tr):
    """Return (errors, warnings) for one brief."""
    errs, warns = [], []
    if not wf.exists(): errs.append(f"missing {wf}")
    else:
        try:
            d = json.loads(wf.read_text())
            if not (d.get("workflow_id") and isinstance(d.get("workflow"), dict)):
                errs.append(f"{wf.name} is not a freya.export_workflow file (no workflow_id/workflow); was it a --dry-run build?")
        except ValueError as e: errs.append(f"{wf.name} is not valid JSON: {e}")
    if tr is None: errs.append(f"no traces/{stem}-*.trace.txt")
    else:
        text = tr.read_text(errors="replace")
        if trace_mod.redact(text) != text: errs.append(f"{tr.name} contains an API key or secret; remove it before committing")
        if "[END]" not in text: warns.append(f"{tr.name} has no [END] line (run unfinished?)")
        elif not re.search(r"\[END\].*status=ok", text): warns.append(f"{tr.name} did not end with status=ok")
        if "dry-run" in text.lower() and "FREYA" not in text: warns.append(f"{tr.name} looks like a dry run")
    return errs, warns


def source_manifest(team, members, repo, command, mock_url, workflow, trace_text, workflow_path, trace_path):
    """Build the folder-task manifest from a successful run, not packaging HEAD."""
    if not team or team.startswith('<') or not members or any(not m.get('name') or '@' not in m.get('email','') for m in members):
        raise ValueError('provide the actual team name and member names/emails')
    if '{case_folder}' not in command:
        raise ValueError('run_command must include {case_folder}')
    if not mock_url.startswith('https://'):
        raise ValueError('mock_url must be the persistent HTTPS deployment')
    if not re.search(r'\[END\].*status=ok', trace_text):
        raise ValueError('the source build did not finish successfully')
    revision = re.search(r'\[START\].*build_commit=([0-9a-f]{40})', trace_text)
    if not revision:
        raise ValueError('folder trace does not identify the commit that ran')
    if not workflow.get('workflow_id') or not isinstance(workflow.get('workflow'),dict):
        raise ValueError('workflow must be a real platform export')
    if 'workflow_id='+workflow['workflow_id'] not in trace_text:
        raise ValueError('export and build trace refer to different workflows')
    return {'team':team,'members':members,'repo':repo,'commit':revision.group(1),
            'run_command':command,'workflow':workflow_path,'trace':trace_path,'mock_url':mock_url}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stems", nargs="+")
    ap.add_argument("--out", default="out"); ap.add_argument("--traces", default="traces"); ap.add_argument("--dest", default="submission")
    ap.add_argument("--team", default="<team name>")
    ap.add_argument("--repo", help="override repo URL (default: git remote origin)")
    ap.add_argument("--manifest", action="store_true", help="create the document-folder submission.json and include complete model transcript")
    ap.add_argument("--members-file", help="JSON list of actual member name/email objects")
    ap.add_argument("--mock-url", help="persistent mock deployment URL")
    ap.add_argument("--run-command", help="folder build command, including literal {case_folder}")
    ap.add_argument("--apply", action="store_true", help="copy and git add -f (default is a dry run)")
    ap.add_argument("--commit", action="store_true", help="with --apply: commit the files (no push)")
    a = ap.parse_args()
    if a.manifest and (len(a.stems) != 1 or not a.members_file or not a.mock_url or not a.run_command):
        ap.error('--manifest needs one stem, --members-file, --mock-url and --run-command')
    out, tdir, dest = ROOT / a.out, ROOT / a.traces, ROOT / a.dest
    plan, bad = [], False
    for stem in a.stems:
        wf, tr = out / f"{stem}.workflow.json", newest_trace(tdir, stem)
        errs, warns = check(stem, wf, tr)
        for m in errs: print(f"ERROR [{stem}] {m}"); bad = True
        for m in warns: print(f"WARN  [{stem}] {m}")
        plan.append((stem, wf, tr, dest / f"{stem}.workflow.json", dest / "traces" / f"{stem}.log"))
    if bad: print("\nFix the errors above first. Nothing copied."); sys.exit(1)
    manifest = None
    if a.manifest:
        stem,wf,tr,dwf,dtr=plan[0]
        model_log=tr.with_name(tr.name.replace('.trace.txt','.model.jsonl'))
        if not model_log.exists():
            ap.error('missing complete model request/response transcript: '+str(model_log))
        repo=a.repo or git('remote','get-url','origin')
        repo=re.sub(r':\/\/[^@/]*@', '://', repo)
        members=json.loads(Path(a.members_file).read_text(encoding='utf-8-sig'))
        manifest=source_manifest(a.team,members,repo,a.run_command,a.mock_url,
            json.loads(wf.read_text(encoding='utf-8')),tr.read_text(encoding='utf-8'),
            dwf.relative_to(ROOT).as_posix(),dtr.relative_to(ROOT).as_posix())
        model_text=model_log.read_text(encoding='utf-8')
        if trace_mod.redact(model_text)!=model_text:
            ap.error('model transcript contains unredacted credentials')
        print(json.dumps(manifest,ensure_ascii=False,indent=2))
    for stem, wf, tr, dwf, dtr in plan:
        print(f"{'copy' if a.apply else 'would copy'}: {wf.relative_to(ROOT)} -> {dwf.relative_to(ROOT)} ; {tr.relative_to(ROOT)} -> {dtr.relative_to(ROOT)}")
        if a.apply:
            dtr.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(wf, dwf); shutil.copyfile(tr, dtr)
            if a.manifest:
                with dtr.open('a',encoding='utf-8') as log:
                    log.write('\n--- Complete builder model session (requests and responses) ---\n'+model_text)
            git("add", "-f", str(dwf), str(dtr))
    if manifest and a.apply:
        manifest_path=dest/'submission.json'
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        git('add','-f',str(manifest_path))
    if a.apply and a.commit:
        git("commit", "-m", "Submission: workflow exports and traces for " + ", ".join(a.stems), "--", *[str(p) for _, _, _, x, y in plan for p in (x, y)], *([str(manifest_path)] if manifest else []))
        print("committed (not pushed). Push before sending the form.")
    commit = git("rev-parse", "HEAD")
    if not (a.apply and a.commit):
        print("\nNOTE: commit below is the current HEAD. The submission files are not in it until you commit and push; rerun after committing.")
    try: repo = a.repo or git("remote", "get-url", "origin")
    except Exception: repo = a.repo or "<repo url>"
    repo = re.sub(r"://[^@/]*@", "://", repo)
    paths = lambda p: ", ".join(str(x.relative_to(ROOT)) for x in p)
    print("\n--- form fields ---")
    print(f"team: {a.team}\nrepo: {repo}\ncommit: {commit}\nrun_command: {RUN_CMD.replace('traces/{stem}.log', 'traces/<stem>.log')}")
    print("workflows: " + paths([p[3] for p in plan])); print("traces: " + paths([p[4] for p in plan]))
    if git("status", "--porcelain", "--", a.dest) and not a.apply: print("(submission/ has uncommitted changes)")
    print("unpushed commits:", git("rev-list", "--count", "@{u}..HEAD", check=False) or "unknown (no upstream)")


if __name__ == "__main__":
    main()
