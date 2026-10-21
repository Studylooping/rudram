#!/bin/bash
# One-time setup of a render environment (CPU). Needs HF_TOKEN with access to ai4bharat/indic-parler-tts.
# Adapted from the sister project Studylooping/Chandi (scripts/setup_render.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=${VENV:-$HOME/rudram-venv}
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  "$VENV/bin/pip" install -q git+https://github.com/huggingface/parler-tts.git
  # parler-tts may pull a mismatched torch/torchaudio; pin the CPU pair again
  "$VENV/bin/pip" install -q torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  "$VENV/bin/pip" install -q indic_transliteration==2.3.82 pylibrb==0.1.2 soundfile pytest librosa==1.0.0 pyworld==0.3.5
fi
echo PIP_DONE
# aligner checkpoint (1.26 GB): resumable download with a size check
CK=$HOME/.cache/torch/hub/checkpoints/model.pt
mkdir -p "$(dirname "$CK")"
for i in 1 2 3 4 5 6; do
  [ "$(stat -c %s "$CK" 2>/dev/null || echo 0)" = 1262047414 ] && break
  curl -sS -C - -o "$CK" https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt || sleep 5
done
[ "$(stat -c %s "$CK")" = 1262047414 ] || { echo "aligner download incomplete"; exit 1; }
echo SETUP_DONE
