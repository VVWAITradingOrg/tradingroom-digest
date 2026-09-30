#!/usr/bin/env /usr/bin/python3
"""Bound a CLI model call and terminate only its own process group on timeout."""
import os
import signal
import subprocess
import sys

process = subprocess.Popen(
    sys.argv[1:], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
    start_new_session=True,
)
try:
    status = process.wait(timeout=900)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    print("Codex analysis exceeded 900 seconds; source evidence retained.", file=sys.stderr)
    status = 124
sys.exit(status)
