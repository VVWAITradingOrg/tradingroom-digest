#!/usr/bin/env /usr/bin/python3
"""Execute one immutable pipeline snapshot, with an inherited launch lock."""
import fcntl
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
(root/'data').mkdir(exist_ok=True)
handle = (root/'data/pipeline.lock').open('a')
try:
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print('Tradingroom pipeline already running; skip overlapping trigger.', file=sys.stderr)
    sys.exit(0)
os.set_inheritable(handle.fileno(), True)
source = (root/'pipeline.sh').read_text()
os.chdir(root)
os.execv('/bin/bash', ['/bin/bash','-c',source,str(root/'pipeline.sh'),*sys.argv[1:]])
