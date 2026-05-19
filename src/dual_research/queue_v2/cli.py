"""Queue v2 CLI — one subcommand per step plus orchestration helpers.

The CLI is the single externally-supported entrypoint. Each step is
also importable directly (``from dual_research.queue_v2 import read,
reason, ...``), but the CLI is what the dashboard, the trigger
script, and operators use day-to-day.

Subcommands
-----------

    init <spec>...          Seed queue/state.json with the listed spec numbers.
    status                  Print a compact text dashboard to stdout.
    next                    Print the next-up spec number on the queue.

    read <spec>             Step 1.
    reason <spec>           Step 2 (writes reason-notes.md).
    rewrite-skip <spec>     Step 3 fast path — mark skipped.
    rewrite-complete <spec> Step 3 slow path — call after edits land.
                            Reads --edits-file <path> with a JSON array of
                            {"summary": ..., "before": ..., "after": ...}.
    implement-begin <spec>  Step 4 branch checkout.
    implement-complete <spec> --diff "+342 -89 (4 files)"
    verify-begin <spec>     Step 5 — write the planned shot list.
    verify-shot <spec> --index N --captured true|false [--note "..."]
    verify-verdict <spec> --index N --verdict pass|fail [--note "..."]
    verify-finalize <spec>  Step 5 close-out.
    pr-begin <spec>         Step 6 placeholder (sets in_progress).
    pr-push <spec> --branch <name>
    pr-open <spec> --branch <name> [--dry-run]
    pr-complete <spec> --url <url>
    deploy-begin <spec>
    deploy-wait-ci <spec> --url <pr-url>
    deploy-merge <spec> --url <pr-url>     (squash-merge + fly deploy + health probe)
    deploy-complete <spec> --commit X --version Y
    handover <spec> [--next-spec NNNN]     Step 8.

    dashboard               Launch the live dashboard server (port 8089).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="queue-v2")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("next")
    sub.add_parser("dashboard")

    init = sub.add_parser("init")
    init.add_argument("specs", nargs="+", help="spec numbers, e.g. 0092 0093 ...")

    for cmd in ["read", "reason", "rewrite-skip", "implement-begin", "verify-begin",
                "verify-finalize", "pr-begin", "deploy-begin"]:
        sp = sub.add_parser(cmd)
        sp.add_argument("spec")

    sp = sub.add_parser("rewrite-complete")
    sp.add_argument("spec")
    sp.add_argument("--edits-file", required=True)

    sp = sub.add_parser("implement-complete")
    sp.add_argument("spec")
    sp.add_argument("--diff", required=True)

    sp = sub.add_parser("verify-shot")
    sp.add_argument("spec")
    sp.add_argument("--index", type=int, required=True)
    sp.add_argument("--captured", choices=["true", "false"], required=True)
    sp.add_argument("--note", action="append", default=[])

    sp = sub.add_parser("verify-verdict")
    sp.add_argument("spec")
    sp.add_argument("--index", type=int, required=True)
    sp.add_argument("--verdict", choices=["pass", "fail", "skipped"], required=True)
    sp.add_argument("--note")

    sp = sub.add_parser("pr-push")
    sp.add_argument("spec")
    sp.add_argument("--branch", required=True)

    sp = sub.add_parser("pr-open")
    sp.add_argument("spec")
    sp.add_argument("--branch", required=True)
    sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("pr-complete")
    sp.add_argument("spec")
    sp.add_argument("--url", required=True)

    sp = sub.add_parser("deploy-wait-ci")
    sp.add_argument("spec")
    sp.add_argument("--url", required=True)

    sp = sub.add_parser("deploy-merge")
    sp.add_argument("spec")
    sp.add_argument("--url", required=True)
    sp.add_argument("--target-version", required=True)

    sp = sub.add_parser("deploy-complete")
    sp.add_argument("spec")
    sp.add_argument("--commit", required=True)
    sp.add_argument("--version", required=True)

    sp = sub.add_parser("handover")
    sp.add_argument("spec")
    sp.add_argument("--next-spec")

    args = p.parse_args(argv)
    return _dispatch(args)


def _dispatch(args) -> int:
    from dual_research.queue_v2 import (
        deploy, handover, implement, pr, read, reason, rewrite, state,
        verify,
    )

    if args.cmd == "init":
        state.init_queue(args.specs)
        print(f"queue initialised with {len(args.specs)} spec(s)")
        return 0

    if args.cmd == "status":
        s = state.load()
        sys.stdout.write(json.dumps(s.to_dict(), indent=2) + "\n")
        return 0

    if args.cmd == "next":
        s = state.load()
        if s.active:
            print(s.active["spec"])
            return 0
        if s.queue:
            print(s.queue[0])
            return 0
        return 1

    if args.cmd == "dashboard":
        from dual_research.queue_v2.dashboard import server
        server.run()
        return 0

    if args.cmd == "read":
        # begin_spec must run before read.run, because read.run calls
        # state.begin_step which requires an active spec. Peek at the
        # spec file just enough to extract the slug.
        from dual_research.queue_v2 import parse_spec
        spec_path = read.find_spec(args.spec)
        s = state.load()
        if s.active is None or s.active.get("spec") != args.spec.zfill(4):
            preview = parse_spec.parse(spec_path)
            branch = f"spec/{preview.spec}-{preview.slug}"
            state.begin_spec(preview.spec, preview.slug, branch)
        parsed = read.run(args.spec)
        print(f"read spec {parsed.spec} — {len(parsed.files_touched)} files, {len(parsed.visual_matrix)} matrix rows")
        return 0

    if args.cmd == "reason":
        notes = reason.run(args.spec)
        print(f"reason produced {len(notes)} alignment note(s)")
        return 0

    if args.cmd == "rewrite-skip":
        rewrite.run_skip(args.spec)
        print("rewrite skipped")
        return 0

    if args.cmd == "rewrite-complete":
        edits = json.loads(Path(args.edits_file).read_text())
        rewrite.run_complete(args.spec, edits)
        print(f"rewrite complete — {len(edits)} edit(s) logged")
        return 0

    if args.cmd == "implement-begin":
        branch = implement.begin(args.spec)
        print(branch)
        return 0

    if args.cmd == "implement-complete":
        implement.complete(args.spec, args.diff)
        print("implement complete")
        return 0

    if args.cmd == "verify-begin":
        shots = verify.begin(args.spec)
        print(json.dumps([s.__dict__ for s in shots], indent=2))
        return 0

    if args.cmd == "verify-shot":
        verify.record_shot(
            args.spec,
            args.index,
            captured=(args.captured == "true"),
            notes=args.note,
        )
        return 0

    if args.cmd == "verify-verdict":
        verify.record_verdict(args.spec, args.index, args.verdict, args.note)
        return 0

    if args.cmd == "verify-finalize":
        ok = verify.finalize(args.spec)
        print("pass" if ok else "fail")
        return 0 if ok else 1

    if args.cmd == "pr-begin":
        pr.begin(args.spec)
        return 0

    if args.cmd == "pr-push":
        pr.push_branch(args.branch)
        return 0

    if args.cmd == "pr-open":
        url = pr.open_pr(args.spec, args.branch, dry_run=args.dry_run)
        print(url)
        return 0

    if args.cmd == "pr-complete":
        pr.complete(args.spec, args.url)
        return 0

    if args.cmd == "deploy-begin":
        deploy.begin(args.spec)
        return 0

    if args.cmd == "deploy-wait-ci":
        deploy.wait_for_ci(args.url)
        return 0

    if args.cmd == "deploy-merge":
        commit = deploy.squash_merge(args.url)
        deploy.fly_deploy()
        payload = deploy.wait_for_health(args.target_version)
        deploy.complete(args.spec, commit, payload.get("version", "?"))
        print(json.dumps({"commit": commit, "health": payload}, indent=2))
        return 0

    if args.cmd == "deploy-complete":
        deploy.complete(args.spec, args.commit, args.version)
        return 0

    if args.cmd == "handover":
        path = handover.write_and_complete(args.spec, args.next_spec)
        print(path)
        return 0

    print(f"unknown command: {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
