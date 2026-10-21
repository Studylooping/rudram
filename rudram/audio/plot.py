"""Plot one rendered phrase: measured F0 (pYIN) against the target svara levels per syllable.

  python -m rudram.audio.plot --section pilot --unit namaka-1 --phrase 1 --out audio/figures/x.png
"""
import argparse
import glob
import json
import pathlib

import matplotlib
import numpy as np
import soundfile as sf

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from rudram.audio import render  # noqa: E402
from rudram.audio.align import align  # noqa: E402
from rudram.audio.recite import ROOT  # noqa: E402
from rudram.corpus import SECTIONS  # noqa: E402
from rudram.itrans import PITCH, syllabify  # noqa: E402

IAST_C = {'k': 'k', 'kh': 'kh', 'g': 'g', 'gh': 'gh', '~N': 'ṅ', 'ch': 'c', 'Ch': 'ch', 'j': 'j',
          'jh': 'jh', '~n': 'ñ', 'T': 'ṭ', 'Th': 'ṭh', 'D': 'ḍ', 'Dh': 'ḍh', 'N': 'ṇ', 't': 't',
          'th': 'th', 'd': 'd', 'dh': 'dh', 'n': 'n', 'p': 'p', 'ph': 'ph', 'b': 'b', 'bh': 'bh',
          'm': 'm', 'y': 'y', 'r': 'r', 'l': 'l', 'v': 'v', 'sh': 'ś', 'Sh': 'ṣ', 's': 's', 'h': 'h',
          'L': 'ḻ', 'M': 'ṃ', 'H': 'ḥ', 'gm': 'ṃ'}
IAST_V = {'a': 'a', 'A': 'ā', 'i': 'i', 'I': 'ī', 'u': 'u', 'U': 'ū', 'R': 'ṛ', 'RR': 'ṝ', 'LR': 'ḷ',
          'LRR': 'ḹ', 'e': 'e', 'ai': 'ai', 'o': 'o', 'au': 'au'}


def iast(s):
    mark = {'A': '\u0331', 'S': '\u0301', 'D': '\u030b'}.get(s.svara, '')  # macron below / acute / double acute
    return (''.join(IAST_C[c] for c in s.onset) + IAST_V[s.vowel][0] + mark + IAST_V[s.vowel][1:]
            + ''.join(IAST_C[c] for c in s.coda))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', default='pilot')
    ap.add_argument('--unit', required=True)
    ap.add_argument('--phrase', type=int, required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    unit = next(u for u in SECTIONS[a.section]() if u['id'] == a.unit)
    syls, _ = syllabify(unit['phrases'][a.phrase - 1][0])
    wav = max(glob.glob(str(ROOT / 'out' / 'phrases' / '*' / f'{a.unit}_{a.phrase:03d}_*.wav')),
              key=lambda f: pathlib.Path(f).stat().st_mtime)
    w, sr = sf.read(wav, dtype='float32')
    rep = json.loads(pathlib.Path(wav).with_suffix('.json').read_text(encoding='utf-8'))
    al = align(w, sr, syls)
    t, f0, v = render.f0_track(w, sr)
    st = np.where(v, 12 * np.log2(np.where(v, f0, 1) / render.BASE_HZ), np.nan)
    bounds = list(al['cons_start']) + [al['end']]
    fig, ax = plt.subplots(figsize=(max(8, len(syls) * 0.55), 3.6))
    colours = {'low': '#3b6fb6', 'mid': '#777777', 'high': '#c0392b'}
    for k, s in enumerate(syls):
        lev = render.LEVELS[PITCH[s.svara]]
        ax.plot([bounds[k], bounds[k + 1]], [lev, lev], color=colours[PITCH[s.svara]], lw=6, alpha=0.35,
                solid_capstyle='butt')
        ax.text((bounds[k] + bounds[k + 1]) / 2, -3.3, iast(s), ha='center', fontsize=9)
    ax.plot(t, st, 'k.', ms=2, label='measured F0 (pYIN)')
    ax.set_ylim(-3.8, 2.6)
    ax.set_xlim(0, al['end'] + 0.05)
    ax.set_yticks([-2, 0, 1], ['anudātta −2', 'udātta/pracaya 0', 'svarita +1'])
    ax.set_xlabel('s')
    ax.set_title(f"{a.unit} phrase {a.phrase}: {'compliant' if rep['ok'] else 'NOT compliant'} "
                 f"(max pitch error {rep['max_pitch_err_st']} st, max duration error {rep['max_dur_err']:.0%})",
                 fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=110)
    print(a.out)


if __name__ == '__main__':
    main()
