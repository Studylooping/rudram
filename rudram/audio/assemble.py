"""Concatenate the published unit mp3s in traditional order into audio/01_Namaka.mp3 and
audio/02_Chamaka.mp3 (with the unit pause between units) and rebuild audio/README.md from the
unit reports.

  python -m rudram.audio.assemble [--partial] [--push]
Without --partial a section is only assembled when all its units are published.
"""
import argparse
import json
import subprocess
import tempfile

import numpy as np
import soundfile as sf

from rudram.audio import publish
from rudram.audio.publish import REPORTS, ROOT, run, unit_mp3
from rudram.corpus import PAUSE, SECTIONS

U = 0.125  # seconds per mAtrA (the render tempo)
OUT = {'namaka': '01_Namaka.mp3', 'chamaka': '02_Chamaka.mp3'}
TITLES = {'namaka': 'Namaka (dhyAna, TS 4.5 anuvAkas 1-11, closing mantras)',
          'chamaka': 'Camaka (TS 4.7 anuvAkas 1-11, closing mantras)'}


def decode(mp3, sr=44100):
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        run('ffmpeg', '-v', 'error', '-y', '-i', str(mp3), '-ac', '1', '-ar', str(sr), f.name)
        w, _ = sf.read(f.name, dtype='float32')
    return w


def unit_stats(unit):
    rep = json.loads((REPORTS / f'{unit}.json').read_text(encoding='utf-8'))
    return dict(n=len(rep), ok=sum(x['ok'] for x in rep), dur=sum(x['durations_ok'] for x in rep),
                pit=sum(x['pitch_ok'] for x in rep), syl=sum(len(x['svara']) for x in rep),
                syl_dur=sum(abs(e) <= 0.2 for x in rep for e in x['dur_errors']),
                syl_pit=sum(e is not None and abs(e) <= 0.5 for x in rep for e in x['pitch_errors_st']),
                bad=[str(x['phrase']) for x in rep if not x['ok']])


def assemble(partial=False):
    order = publish.unit_order()
    built = {}
    for sec, out in OUT.items():
        units = [u['id'] for u in SECTIONS[sec]()]
        have = [u for u in units if unit_mp3(u, order).exists() and (REPORTS / f'{u}.json').exists()]
        missing = [u for u in units if u not in have]
        if (missing and not partial) or not have:
            print(f'{sec}: not assembled, missing units: {", ".join(missing)}')
            continue
        sr = 44100
        gap = np.zeros(int(sr * PAUSE['unit'] * U), dtype=np.float32)
        parts = []
        for u in have:
            parts += [decode(unit_mp3(u, order), sr), gap]
        with tempfile.NamedTemporaryFile(suffix='.wav') as f:
            sf.write(f.name, np.concatenate(parts[:-1]), sr)
            run('ffmpeg', '-v', 'error', '-y', '-i', f.name, '-ac', '1', '-b:a', '128k',
                '-metadata', f'title={TITLES[sec]}', '-metadata', 'album=Sri Rudram (svara)',
                str(ROOT / 'audio' / out))
        built[sec] = (have, missing)
        print(f'{sec}: {out} from {len(have)} units' + (f' (MISSING: {", ".join(missing)})' if missing else ''))
    return built


def write_readme(built):
    order = publish.unit_order()
    lines = ['# Recitation audio\n',
             'Voice: AI4Bharat Indic Parler-TTS (speaker "Aryan"), time-stretched per syllable (Rubber Band',
             'R3, formants preserved) and pitch-set per syllable (WORLD vocoder, spectral envelope kept).',
             f'Tempo 1 mātrā = {U} s. Rules: `../RULES.md`; text sources and svara cross-check: `../TEXT.md`.\n',
             'A phrase is **compliant** only if, measured on the final audio, every syllable is within ±20 %',
             'of its mātrā target (forced re-alignment) *and* within ±0.5 semitone of its svara level',
             '(pYIN F0: anudātta −2, udātta/pracaya 0, svarita +1 semitone re 120 Hz). Non-compliant phrases',
             'are kept (best of 5 takes) and named below; per-syllable numbers are in `reports/<unit>.json`.',
             'The check covers timing and pitch only, **not pronunciation**; a TTS voice is an approximation',
             'of a trained Vedic reciter.\n', '## Full recitation (traditional order)\n']
    for sec, out in OUT.items():
        if sec in built:
            have, missing = built[sec]
            lines.append(f'- [{out}]({out}) — {TITLES[sec]}' + (f' — **incomplete, missing: {", ".join(missing)}**'
                                                                   if missing else ''))
    lines += ['', '## Units\n',
              '| Unit | File | Phrases compliant | Durations ok | Pitch ok | Syllables: duration ok | '
              'Syllables: pitch ok | Non-compliant phrases |', '|---|---|---|---|---|---|---|---|']
    tot = dict(n=0, ok=0, syl=0, syl_dur=0, syl_pit=0)
    for u in order:
        mp3 = unit_mp3(u, order)
        if not (REPORTS / f'{u}.json').exists() or not mp3.exists():
            lines.append(f'| {u} | not yet rendered | | | | | | |')
            continue
        s = unit_stats(u)
        for k in tot:
            tot[k] += s[k]
        lines.append(f"| {u} | [{mp3.name}](units/{mp3.name}) | {s['ok']}/{s['n']} | {s['dur']}/{s['n']} | "
                     f"{s['pit']}/{s['n']} | {s['syl_dur']}/{s['syl']} | {s['syl_pit']}/{s['syl']} | "
                     f"{', '.join(s['bad']) or '—'} |")
    lines.append(f"| **total** | | **{tot['ok']}/{tot['n']}** | | | **{tot['syl_dur']}/{tot['syl']}** | "
                 f"**{tot['syl_pit']}/{tot['syl']}** | |")
    pilot = ROOT / 'audio' / '00_PILOT_Dhyana-Namaka-anuvaka-1.mp3'
    if pilot.exists():
        lines += ['', f'The pilot ([{pilot.name}]({pilot.name}), `reports/pilot.json`) is the listening test '
                      'made before the full render; its phrases are reused in the units above.']
    lines += [''] + [f'![{f.stem}](figures/{f.name})' for f in sorted((ROOT / 'audio' / 'figures').glob('*.png'))]
    (ROOT / 'audio' / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--partial', action='store_true', help='assemble sections with missing units too')
    ap.add_argument('--push', action='store_true')
    a = ap.parse_args()
    built = assemble(a.partial)
    write_readme(built)
    if a.push:
        paths = [str(ROOT / 'audio' / 'README.md')] + [str(ROOT / 'audio' / OUT[s]) for s in built]
        run('git', 'add', *paths)
        if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
            run('git', 'commit', '-m', 'Assemble Namaka / Camaka and update the compliance table' + publish.TRAILER,
                '--', *paths)
            publish.push('assembled sections')


if __name__ == '__main__':
    main()
