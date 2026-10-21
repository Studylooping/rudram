"""Publish finished section renders: out/<section>_<engine>.wav -> audio/<nn>_<name>.mp3,
audio/reports/<section>.json and the compliance table in audio/README.md; commit and push.

  python -m rudram.audio.publish --sections pilot
(adapted from Studylooping/Chandi chandi/audio/publish.py)
"""
import argparse
import json
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
BRANCH = 'claude/rudram-svara-audio'
TRAILER = ('\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n'
           'Claude-Session: https://claude.ai/code/session_01TRJmw72DzoZNhLcE7aUrSD')


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
        'Voice: AI4Bharat Indic Parler-TTS (speaker "Aryan"), time-stretched and pitch-shifted per\n'
        'syllable (Rubber Band R3, formants preserved). Tempo 1 mātrā = 0.125 s. Rules: `../RULES.md`.\n\n'
        'A phrase is **compliant** only if, measured on the final audio, every syllable is within ±20 %\n'
        'of its mātrā target (forced re-alignment) *and* within ±0.5 semitone of its svara level\n'
        '(pYIN F0: anudātta −2, udātta/pracaya 0, svarita +1 semitone re 120 Hz). Per-syllable numbers\n'
        'are in `reports/<section>.json`. The check covers timing and pitch only, **not pronunciation**;\n'
        'a TTS voice is an approximation of a trained Vedic reciter.\n\n'
        '| File | Length | Phrases compliant | Durations ok | Pitch ok | Syllables: duration ok | '
        'Syllables: pitch ok | Non-compliant phrases (unit/phrase) |\n'
        '|---|---|---|---|---|---|---|---|\n' + '\n'.join(rows) + '\n', encoding='utf-8')


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
    for attempt in range(5):
        try:
            run('git', 'push', '-u', 'origin', BRANCH)
            print('published', sections, flush=True)
            return
        except subprocess.CalledProcessError as e:
            print('push retry', attempt + 1, e.stderr.strip()[-200:], flush=True)
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError('push failed after retries')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections', required=True, help='comma-separated')
    publish([s for s in ap.parse_args().sections.split(',') if s])
