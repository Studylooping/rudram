"""Svara-faithful rendering: TTS -> syllable alignment -> time-map stretch -> per-syllable pitch
shift -> verify (re-alignment for durations, F0 tracking for svara pitch).

Time handling (TTS engine, Rubber Band stretch, piecewise time map) is adapted from the sister
project Studylooping/Chandi (chandi/audio/render.py). Pitch control and pitch verification are
new here. The duration and pitch model is documented in RULES.md.
"""
import dataclasses

import librosa
import numpy as np
import pylibrb
import torch

from rudram.audio.align import align, iois
from rudram.itrans import PITCH

# relative pitch of each svara class in semitones above the base (RULES.md section 2)
LEVELS = {'low': -2.0, 'mid': 0.0, 'high': 1.0}
PITCH_TOL = 0.5      # semitones: half the smallest gap between levels
DUR_TOL = 0.2        # relative, per syllable (as in Chandi)
BASE_HZ = 120.0      # reciter's mid (udAtta / pracaya) pitch; see RULES.md
VERSION = 2          # bump when the rendering changes (invalidates the phrase cache)


def matras(syls):
    """Target length of each syllable (vowel onset to next vowel onset) in mAtrAs:
    vowel quantity (hrasva 1, dIrgha 2, pluta 3) + 1/2 per following consonant sound
    (anusvAra, visarga, cluster), TPr 1.34-1.37, 17.5. The Taittiriya anusvAra "gum" counts as
    two consonant sounds [g] + [M]."""
    out = []
    for s in syls:
        extra = sum(1 for c in s.coda if c == 'gm')  # gm = g + M: one more half mAtrA
        out.append(s.matra + 0.5 * (s.post + extra))
    return out


def tts_text(syls):
    """Devanagari for the TTS voice (no svara marks). The Taittiriya anusvAra before r / spirants
    is written गुं so the voice says [guM] (RULES.md section 4)."""
    out = []
    for s in syls:
        if s.word_start and out:
            out.append(' ')
        coda = list(s.coda)
        t = dataclasses.replace(s, coda=[c for c in coda if c != 'gm'], svara='U').dev()
        if 'gm' in coda:
            t += 'गुं'
        out.append(t)
    return ''.join(out) + '।'  # a closing danda: the voice ends the phrase naturally


class ParlerEngine:
    """ai4bharat/indic-parler-tts, speaker "Aryan". Gated on Hugging Face: needs HF_TOKEN."""
    name = 'parler-aryan'
    DESC = ('Aryan speaks in a slow, deep, calm and measured voice, with very clear audio, '
            'no background noise and a close-sounding recording.')

    def __init__(self):
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        mid = 'ai4bharat/indic-parler-tts'
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(mid).eval()
        self.tok = AutoTokenizer.from_pretrained(mid)
        self.dtok = AutoTokenizer.from_pretrained(self.model.config.text_encoder._name_or_path)
        self.sr = self.model.config.sampling_rate

    def synth(self, text, seed=0):
        torch.manual_seed(seed)
        d = self.dtok(self.DESC, return_tensors='pt')
        p = self.tok(text, return_tensors='pt')
        with torch.inference_mode():
            a = self.model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                    prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        return a[0].numpy().astype(np.float32)


def _rb(wave, sr, ratio=1.0, pitch=1.0):
    """Constant-ratio Rubber Band stretch / pitch shift (offline, R3 engine, formants preserved)."""
    opts = (pylibrb.Option.PROCESS_OFFLINE | pylibrb.Option.ENGINE_FINER
            | pylibrb.Option.FORMANT_PRESERVED)
    rb = pylibrb.RubberBandStretcher(sample_rate=sr, channels=1, options=opts,
                                     initial_time_ratio=ratio, initial_pitch_scale=pitch)
    audio = np.ascontiguousarray(wave[np.newaxis, :], dtype=np.float32)
    rb.set_expected_input_duration(audio.shape[1])
    rb.study(audio, final=True)
    rb.process(audio, final=True)
    return rb.retrieve(rb.available())[0]


class _OLA:
    """Overlap-add buffer with half-sine fades of f samples at segment edges."""

    def __init__(self, n, f):
        self.out = np.zeros(n + 2 * f, dtype=np.float32)
        self.w = np.zeros_like(self.out)
        self.f, self.n = f, n

    def add(self, seg, at):
        f = self.f
        env = np.ones(len(seg), dtype=np.float32)
        if f and len(seg) > 2 * f:
            ramp = np.sin(np.linspace(0, np.pi / 2, f, dtype=np.float32)) ** 2
            env[:f], env[-f:] = ramp, ramp[::-1]
        lo, hi = max(at, 0), min(at + len(seg), len(self.out))
        if hi > lo:
            self.out[lo:hi] += (seg * env)[lo - at:hi - at]
            self.w[lo:hi] += env[lo - at:hi - at]

    def result(self):
        w = self.w.copy()
        w[w == 0] = 1
        return (self.out / w)[: self.n]


def stretch(wave, sr, anchors_in, anchors_out, ctx=0.06, fade=0.008):
    """Piecewise time map (Chandi): input times anchors_in[k] land at output times anchors_out[k];
    each segment is stretched with ctx seconds of context and crossfaded to its neighbours."""
    n_out = int(round((anchors_out[-1] + (len(wave) / sr - anchors_in[-1])) * sr))
    f = int(fade * sr)
    ola = _OLA(n_out, f)
    a0 = int(anchors_in[0] * sr)
    ola.add(wave[: a0 + f // 2], 0)
    for k in range(len(anchors_in) - 1):
        ti0, ti1, to0, to1 = anchors_in[k], anchors_in[k + 1], anchors_out[k], anchors_out[k + 1]
        ratio = (to1 - to0) / max(ti1 - ti0, 1e-3)
        c0, c1 = max(ti0 - ctx, 0), min(ti1 + ctx, len(wave) / sr)
        y = _rb(wave[int(c0 * sr): int(c1 * sr)], sr, ratio)
        s0 = int(round((ti0 - c0) * ratio * sr)) - f // 2
        s1 = int(round((ti1 - c0) * ratio * sr)) + f // 2
        ola.add(y[max(s0, 0): s1], int(round(to0 * sr)) - f // 2)
    ola.add(wave[int(anchors_in[-1] * sr) - f // 2:], int(round(anchors_out[-1] * sr)) - f // 2)
    return ola.result()


def pitch_map(wave, sr, bounds, scales, ctx=0.05, fade=0.010):
    """Shift segment k = [bounds[k], bounds[k+1]) by pitch factor scales[k] (time unchanged),
    each with ctx seconds of context, joined with crossfades."""
    f = int(fade * sr)
    ola = _OLA(len(wave), f)
    edges = [0.0] + list(bounds[1:-1]) + [len(wave) / sr]
    for k, sc in enumerate(scales):
        t0, t1 = edges[k], edges[k + 1]
        c0, c1 = max(t0 - ctx, 0), min(t1 + ctx, len(wave) / sr)
        seg = wave[int(c0 * sr): int(c1 * sr)]
        y = _rb(seg, sr, 1.0, sc) if abs(sc - 1) > 1e-3 else seg
        y = np.pad(y, (0, max(0, len(seg) - len(y))))[: len(seg)]
        s0 = int(round((t0 - c0) * sr)) - f // 2
        s1 = int(round((t1 - c0) * sr)) + f // 2
        ola.add(y[max(s0, 0): s1], int(round(t0 * sr)) - f // 2)
    return ola.result()


_F0_SR = 16000


def f0_track(wave, sr):
    w = librosa.resample(wave.astype(np.float32), orig_sr=sr, target_sr=_F0_SR)
    f0, voiced, _ = librosa.pyin(w, fmin=65, fmax=250, sr=_F0_SR, frame_length=1024, hop_length=80)
    t = librosa.times_like(f0, sr=_F0_SR, hop_length=80)
    return t, f0, voiced


def syllable_pitch(wave, sr, al, track=None):
    """Median F0 (semitones re BASE_HZ) of each syllable's voiced nucleus: frames from the vowel
    onset to the start of the next syllable's onset consonants (to speech end for the last).
    None where fewer than 3 voiced frames are found."""
    t, f0, voiced = track or f0_track(wave, sr)
    ons, nxt = al['onsets'], list(al['cons_start'][1:]) + [al['end']]
    out = []
    for o, e in zip(ons, nxt):
        e = max(e, o + 0.04)
        m = (t >= o) & (t < e) & voiced & np.isfinite(f0)
        out.append(float(12 * np.log2(np.median(f0[m]) / BASE_HZ)) if m.sum() >= 3 else None)
    return out


def check_rhythm(durations, targets, tol=DUR_TOL):
    """Fit the unit u (least squares) and compare every syllable to m * u."""
    u = sum(d * m for d, m in zip(durations, targets)) / sum(m * m for m in targets)
    errors = [d / (m * u) - 1 for d, m in zip(durations, targets)]
    return all(abs(e) <= tol for e in errors), u, errors


def check_pitch(measured, syls, tol=PITCH_TOL):
    """Each syllable's measured level must be within tol semitones of its svara's target level
    (so the nearest level is the right class). Unmeasured syllables fail."""
    errs = []
    for m, s in zip(measured, syls):
        errs.append(None if m is None else m - LEVELS[PITCH[s.svara]])
    ok = all(e is not None and abs(e) <= tol for e in errs)
    return ok, errs


@dataclasses.dataclass
class PhraseResult:
    audio: np.ndarray
    ok: bool
    dur_ok: bool
    pitch_ok: bool
    u: float
    dur_errors: list
    pitch_errors: list
    seed: int
    notes: list


def _fill(vals, default=0.0):
    """Replace None by the nearest measured neighbour (default if none)."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    if not idx:
        return [default] * len(vals)
    return [v if v is not None else vals[min(idx, key=lambda j: abs(j - i))] for i, v in enumerate(vals)]


def render_phrase(engine, syls, u, targets=None, seeds=(0, 1, 2, 3), refine=2):
    """Render one phrase to mAtrA timing and svara pitch; verify; retry other seeds on failure.
    Returns the first verified take, else the best one (reported as non-compliant).
    targets: per-syllable mAtrAs (default: the Vedic model, matras())."""
    sr = engine.sr
    targets = targets or matras(syls)
    want = [LEVELS[PITCH[s.svara]] for s in syls]
    text = tts_text(syls)
    best, notes = None, []
    for seed in seeds:
        raw = engine.synth(text, seed)
        if len(raw) < 0.06 * sr * len(syls):
            notes.append(f'seed {seed}: clip of {len(raw) / sr:.2f}s'); continue
        try:
            al = align(raw, sr, syls)
        except RuntimeError as e:
            notes.append(f'seed {seed}: align {e}'); continue
        # 1. time map: vowel onset i -> lead + sum(targets[:i]) * u ; speech end -> lead + total
        a_in, a_out, t = [], [], al['onsets'][0]
        for o, m in zip(al['onsets'], targets):
            a_in.append(o); a_out.append(t); t += m * u
        a_in.append(al['end']); a_out.append(t)
        out = stretch(raw, sr, a_in, a_out)
        # 2. pitch: shift every syllable segment (onset consonants .. next onset consonants)
        #    so its nucleus lands on its svara level; repeat on the residual error
        for _ in range(refine + 1):
            al = align(out, sr, syls)
            meas = syllable_pitch(out, sr, al)
            dur_ok, u_fit, derr = check_rhythm(iois(al['onsets'], al['end']), targets)
            pitch_ok, perr = check_pitch(meas, syls)
            if dur_ok and pitch_ok:
                break
            if not dur_ok:  # correction pass: move the measured onsets onto the targets again
                lead = al['onsets'][0] - a_out[0]
                out = stretch(out, sr, al['onsets'] + [al['end']], [a + lead for a in a_out])
                al = align(out, sr, syls)
                meas = syllable_pitch(out, sr, al)
            shift = [w - m for w, m in zip(want, _fill(meas))]
            if any(abs(s) > 0.05 for s in shift):
                bounds = list(al['cons_start']) + [al['end']]
                out = pitch_map(out, sr, bounds, [2 ** (s / 12) for s in shift])
        else:
            al = align(out, sr, syls)
            meas = syllable_pitch(out, sr, al)
            dur_ok, u_fit, derr = check_rhythm(iois(al['onsets'], al['end']), targets)
            pitch_ok, perr = check_pitch(meas, syls)
        res = PhraseResult(out[: int(al['end'] * sr) + int(0.05 * sr)], dur_ok and pitch_ok, dur_ok,
                           pitch_ok, u_fit, derr, perr, seed, notes)
        if res.ok:
            return res
        if best is None or _badness(res) < _badness(best):
            best = res
    if best is None:
        raise RuntimeError(f'{text}: no usable take ({"; ".join(notes)})')
    return best


def _badness(r):
    p = [abs(e) if e is not None else 3.0 for e in r.pitch_errors]
    return (sum(abs(e) > DUR_TOL for e in r.dur_errors) + sum(x > PITCH_TOL for x in p),
            max(map(abs, r.dur_errors)) + max(p) / 3)


def silence(sr, n_matras, u):
    return np.zeros(int(sr * n_matras * u), dtype=np.float32)
