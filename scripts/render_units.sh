#!/bin/bash
# Render the given units of a section (resumable phrase cache) and publish each finished unit
# to the branch (audio/units/<NN>_<unit>.mp3 + audio/reports/<unit>.json). Several sessions can run
# on disjoint units. Prints ALL_DONE and exits 0 only when every listed unit is published.
#   scripts/render_units.sh namaka namaka-2 namaka-3
# One-time setup first: scripts/setup_render.sh (needs HF_TOKEN).
cd "$(dirname "$0")/.."
VENV=${VENV:-$HOME/rudram-venv}
section=$1; shift
status=0
for u in "$@"; do
  if [ -f "audio/reports/$u.json" ]; then echo "=== $u already published"; continue; fi
  echo "=== $u start $(date -u +%H:%M)"
  rm -f "out/units/$u.wav" "out/units/$u.json"
  "$VENV/bin/python" -m rudram.audio.recite --section "$section" --units "$u" --unit-out 2>&1 \
    | grep -aE --line-buffered "verified|COMPLIANT|FAILED|Error|Traceback"
  if [ -f "out/units/$u.wav" ] && [ -f "out/units/$u.json" ]; then
    "$VENV/bin/python" -m rudram.audio.publish --units "$u" 2>&1 | tail -3
    [ -f "audio/reports/$u.json" ] || status=1
  else
    echo "=== $u incomplete (some phrases failed); rerun to retry"; status=1
  fi
  echo "=== $u done $(date -u +%H:%M)"
done
[ $status -eq 0 ] && echo ALL_DONE
exit $status
