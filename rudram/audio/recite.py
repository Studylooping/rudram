"""Recite a section to a WAV file with a per-phrase compliance report.

  python -m rudram.audio.recite --section pilot [--u 0.125]

Every phrase is rendered by render_phrase (mAtrA timing + svara pitch, verified). Rendered
phrases are cached in out/phrases/ so an interrupted run resumes where it stopped.
"""
import argparse
import hashlib
import json
import pathlib

import numpy as np
import soundfile as sf

from rudram.audio import render
from rudram.audio.render import render_phrase, silence
from rudram.corpus import PAUSE, SECTIONS, weights
from rudram.itrans import devanagari, syllabify

ROOT = pathlib.Path(__file__).resolve().parents[2]


def targets_for(unit, syls):
    if unit['kind'] != 'metre':
        return render.matras(syls)
    m = [1 if w == 'L' else 2 for w in weights(syls)]
    n = unit['pada_len']
    for i in range(n - 1, len(m), n):
        m[i] = 2  # pAdAnta: the last syllable of a pAda is held as guru
    return m


def phrase_report(unit, k, text, syls, targets, r):
    return {'unit': unit['id'], 'phrase': k + 1, 'text': devanagari(syls, marks=True),
            'svara': ''.join(s.svara for s in syls), 'matra': targets,
            'ok': bool(r.ok), 'durations_ok': bool(r.dur_ok), 'pitch_ok': bool(r.pitch_ok),
            'u': round(r.u, 4), 'max_dur_err': round(max(map(abs, r.dur_errors)), 3),
            'dur_errors': [round(e, 3) for e in r.dur_errors],
            'pitch_errors_st': [None if e is None else round(e, 2) for e in r.pitch_errors],
            'max_pitch_err_st': round(max((abs(e) for e in r.pitch_errors if e is not None), default=99), 2),
            'unmeasured': sum(e is None for e in r.pitch_errors), 'seed': r.seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', required=True, choices=sorted(SECTIONS))
    ap.add_argument('--u', type=float, default=0.125, help='seconds per mAtrA')
    ap.add_argument('--units', default='', help='comma-separated unit ids (default: all)')
    a = ap.parse_args()
    units = SECTIONS[a.section]()
    if a.units:
        units = [u for u in units if u['id'] in a.units.split(',')]
    engine = render.ParlerEngine()
    cache = ROOT / 'out' / 'phrases' / f'{engine.name}_u{a.u}'
    cache.mkdir(parents=True, exist_ok=True)
    audio, report, failed = [], [], []
    sr = engine.sr
    for unit in units:
        for k, (text, pause) in enumerate(unit['phrases']):
            syls, notes = syllabify(text)
            targets = targets_for(unit, syls)
            key = hashlib.sha1(json.dumps([text, targets, render.LEVELS, render.BASE_HZ, render.VERSION]).encode()).hexdigest()[:12]
            stem = cache / f"{unit['id']}_{k + 1:03d}_{key}"
            if stem.with_suffix('.wav').exists() and stem.with_suffix('.json').exists():
                w, _ = sf.read(stem.with_suffix('.wav'), dtype='float32')
                rep = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
            else:
                try:
                    r = render_phrase(engine, syls, a.u, targets=targets)
                except Exception as e:  # noqa: BLE001 - keep going; retried on the next run
                    failed.append(f"{unit['id']} {k + 1}: {e}")
                    print(f"FAILED {unit['id']} {k + 1}: {e}", flush=True)
                    continue
                w = r.audio
                rep = phrase_report(unit, k, text, syls, targets, r)
                rep['notes'] = notes + r.notes
                sf.write(stem.with_suffix('.wav'), w, sr)
                stem.with_suffix('.json').write_text(json.dumps(rep, ensure_ascii=False), encoding='utf-8')
            audio += [w, silence(sr, PAUSE[pause], a.u)]
            report.append(rep)
            print(f"{unit['id']} {k + 1}: {'verified' if rep['ok'] else 'NOT COMPLIANT'} "
                  f"(dur {rep['max_dur_err']:.0%}, pitch {rep['max_pitch_err_st']} st, seed {rep['seed']})", flush=True)
        audio.append(silence(sr, PAUSE['unit'], a.u))
    if failed:
        print(f'{a.section}: {len(failed)} phrase(s) failed, section not written; rerun to retry them')
        raise SystemExit(1)
    out = ROOT / 'out' / f'{a.section}_{engine.name}.wav'
    sf.write(out, np.concatenate(audio), sr)
    out.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{out}: {sum(x["ok"] for x in report)}/{len(report)} phrases verified compliant')


if __name__ == '__main__':
    main()
