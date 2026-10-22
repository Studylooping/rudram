"""Publish finished renders, commit and push (adapted from Studylooping/Chandi publish.py).

  python -m rudram.audio.publish --sections pilot      section file -> audio/<nn>_<name>.mp3
  python -m rudram.audio.publish --units namaka-2,...  out/units/<unit>.wav -> audio/units/<NN>_<unit>.mp3
                                                       + audio/reports/<unit>.json (only those paths)
Several sessions may publish units to the branch at the same time: each commits only its own
files and rebases before pushing.
"""
import argparse
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE = 'parler-aryan'
# traditional order: Mahanyasa, Namaka (dhyana + 11 anuvakas), Camaka; the pilot is listed apart
SECTIONS = ['pilot', 'mahanyasa', 'namaka', 'chamaka']
NAMES = {'pilot': 'PILOT_Dhyana-Namaka-anuvaka-1', 'mahanyasa': 'Mahanyasa', 'namaka': 'Namaka',
         'chamaka': 'Chamaka'}
REPORTS = ROOT / 'audio' / 'reports'
UNITS = ROOT / 'audio' / 'units'
BRANCH = 'claude/rudram-svara-audio'
REMOTE = 'https://github.com/studylooping/rudram'  # lowercase: the push credential is scoped to it
TRAILER = ('\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n'
           'Claude-Session: ' + os.environ.get('RUDRAM_SESSION_URL',
                                              'https://claude.ai/code/session_01TRJmw72DzoZNhLcE7aUrSD'))


def unit_order():
    """All unit ids in traditional recitation order (Namaka with its dhyAna, then Camaka)."""
    from rudram.corpus import SECTIONS as CORPUS
    return [u['id'] for sec in ('namaka', 'chamaka') for u in CORPUS[sec]()]


def unit_mp3(unit, order=None):
    order = order or unit_order()
    return UNITS / f'{order.index(unit):02d}_{unit}.mp3'


def mp3_name(sec):
    return f'{SECTIONS.index(sec):02d}_{NAMES[sec]}.mp3'


def run(*cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def stats(sec):
    rep = json.loads((REPORTS / f'{sec}.json').read_text(encoding='utf-8'))
    n = len(rep)
    ok = sum(x['ok'] for x in rep)
    dur = sum(x['durations_ok'] for x in rep)
    pit = sum(x['pitch_ok'] for x in rep)
    syl = sum(len(x['svara']) for x in rep)
    syl_dur = sum(abs(e) <= 0.2 for x in rep for e in x['dur_errors'])
    syl_pit = sum(e is not None and abs(e) <= 0.5 for x in rep for e in x['pitch_errors_st'])
    bad = [f"{x['unit']}/{x['phrase']}" for x in rep if not x['ok']]
    return dict(n=n, ok=ok, dur=dur, pit=pit, syl=syl, syl_dur=syl_dur, syl_pit=syl_pit, bad=bad)


def duration(path):
    return float(run('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)))


def write_readme():
    rows = []
    for sec in SECTIONS:
        mp3 = ROOT / 'audio' / mp3_name(sec)
        if not (REPORTS / f'{sec}.json').exists() or not mp3.exists():
            continue
        s = stats(sec)
        rows.append(f"| [{mp3.name}]({mp3.name}) | {duration(mp3) / 60:.1f} min | {s['ok']}/{s['n']} | "
                    f"{s['dur']}/{s['n']} | {s['pit']}/{s['n']} | {s['syl_dur']}/{s['syl']} | "
                    f"{s['syl_pit']}/{s['syl']} | {', '.join(s['bad']) or '—'} |")
    (ROOT / 'audio' / 'README.md').write_text(
        '# Recitation audio\n\n'
        'Voice: AI4Bharat Indic Parler-TTS (speaker "Aryan"), time-stretched per syllable (Rubber Band\n'
        'R3, formants preserved) and pitch-set per syllable (WORLD vocoder, spectral envelope kept).\n'
        'Tempo 1 mātrā = 0.125 s. Rules: `../RULES.md`.\n\n'
        'A phrase is **compliant** only if, measured on the final audio, every syllable is within ±20 %\n'
        'of its mātrā target (forced re-alignment) *and* within ±0.5 semitone of its svara level\n'
        '(pYIN F0: anudātta −2, udātta/pracaya 0, svarita +1 semitone re 120 Hz). Per-syllable numbers\n'
        'are in `reports/<section>.json`. The check covers timing and pitch only, **not pronunciation**;\n'
        'a TTS voice is an approximation of a trained Vedic reciter.\n\n'
        '| File | Length | Phrases compliant | Durations ok | Pitch ok | Syllables: duration ok | '
        'Syllables: pitch ok | Non-compliant phrases (unit/phrase) |\n'
        '|---|---|---|---|---|---|---|---|\n' + '\n'.join(rows) + '\n'
        + ''.join(f'\n![{f.stem}](figures/{f.name})\n' for f in sorted((ROOT / 'audio' / 'figures').glob('*.png'))),
        encoding='utf-8')


def publish(sections):
    REPORTS.mkdir(parents=True, exist_ok=True)
    paths = []
    for sec in sections:
        wav = ROOT / 'out' / f'{sec}_{ENGINE}.wav'
        mp3 = ROOT / 'audio' / mp3_name(sec)
        run('ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-ac', '1', '-b:a', '128k',
            '-metadata', f'title={NAMES[sec]}', '-metadata', 'album=Mahanyasa-purvaka Rudra (svara)', str(mp3))
        (REPORTS / f'{sec}.json').write_text(wav.with_suffix('.json').read_text(encoding='utf-8'), encoding='utf-8')
        paths += [str(mp3), str(REPORTS / f'{sec}.json')]
    write_readme()
    run('git', 'add', *paths, str(ROOT / 'audio' / 'README.md'))
    if not subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
        return
    run('git', 'commit', '-m', f'Add recitation audio: {", ".join(sections)}' + TRAILER)
    push(sections)


def push(what):
    for attempt in range(6):
        try:
            run('git', 'pull', '--rebase', '--autostash', REMOTE, BRANCH)
            run('git', 'push', REMOTE, f'HEAD:{BRANCH}')
            print('published', what, flush=True)
            return
        except subprocess.CalledProcessError as e:
            print('push retry', attempt + 1, e.stderr.strip()[-200:], flush=True)
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError('push failed after retries')


def publish_units(units):
    """Encode out/units/<unit>.wav and commit only that unit's mp3 + report."""
    order = unit_order()
    UNITS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    paths = []
    for unit in units:
        wav = ROOT / 'out' / 'units' / f'{unit}.wav'
        mp3 = unit_mp3(unit, order)
        run('ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-ac', '1', '-b:a', '128k',
            '-metadata', f'title={unit}', '-metadata', 'album=Sri Rudram (svara)', str(mp3))
        (REPORTS / f'{unit}.json').write_text(wav.with_suffix('.json').read_text(encoding='utf-8'), encoding='utf-8')
        paths += [str(mp3), str(REPORTS / f'{unit}.json')]
    run('git', 'add', *paths)
    if not subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
        print('nothing new to publish', units, flush=True)
        return
    run('git', 'commit', '-m', f'Add recitation unit audio: {", ".join(units)}' + TRAILER, '--', *paths)
    push(units)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', default='', help='comma-separated section renders')
    ap.add_argument('--units', default='', help='comma-separated units from out/units/')
    a = ap.parse_args()
    if a.units:
        publish_units([s for s in a.units.split(',') if s])
    if a.sections:
        publish([s for s in a.sections.split(',') if s])
