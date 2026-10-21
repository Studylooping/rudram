"""Syllable-level forced alignment (torchaudio MMS_FA), adapted from Studylooping/Chandi
(chandi/audio/align.py), driven by the svara-ITRANS syllables of rudram.itrans.

Timing model (as in Chandi): a syllable's duration is the interval from its vowel onset to the
next syllable's vowel onset (inter-onset interval, IOI); the last syllable of a phrase runs from
its vowel onset to the end of speech.
"""
import numpy as np
import torch
import torchaudio

_bundle = torchaudio.pipelines.MMS_FA
_model = None
SR = _bundle.sample_rate


def _get_model():
    global _model
    if _model is None:
        _model = _bundle.get_model(with_star=False).eval()
    return _model


def align(wave, sr, syls):
    """Return dict with per-syllable vowel onset / vowel end / onset-consonant start (s),
    speech start / end (s)."""
    model, dic = _get_model(), _bundle.get_dict(star=None)
    wave = torch.as_tensor(wave, dtype=torch.float32)
    if sr != SR:
        wave = torchaudio.functional.resample(wave, sr, SR)
    chars, first_cons, vowel_first, vowel_last = [], [], [], []
    for s in syls:
        onset, vow, coda = s.rom()
        first_cons.append(len(chars) if onset else None)
        chars.extend(onset)
        vowel_first.append(len(chars))
        chars.extend(vow)
        vowel_last.append(len(chars) - 1)
        chars.extend(coda)
    tokens = torch.tensor([[dic[c] for c in chars]], dtype=torch.int32)
    with torch.inference_mode():
        emission, _ = model(wave.unsqueeze(0))
        ali, scores = torchaudio.functional.forced_align(emission, tokens, blank=0)
    spans = torchaudio.functional.merge_tokens(ali[0], scores[0].exp())
    ratio = (wave.shape[-1] / SR) / emission.shape[1]
    t = lambda k: spans[k].start * ratio
    start, end = active_region(wave.numpy(), SR)
    end = max(end, spans[-1].end * ratio)
    return {
        'onsets': [t(k) for k in vowel_first],
        'vowel_end': [spans[k].end * ratio for k in vowel_last],
        'cons_start': [t(k) if k is not None else t(v) for k, v in zip(first_cons, vowel_first)],
        'start': start, 'end': end,
        'score': float(np.mean([sp.score for sp in spans])),
    }


def active_region(w, sr, floor_db=-35.0, hop=0.01):
    """First/last time where 10 ms RMS energy is within floor_db of the peak."""
    h = int(hop * sr)
    n = max(len(w) // h, 1)
    rms = (w[: n * h].reshape(n, h) ** 2).mean(axis=1) ** 0.5
    db = 20 * np.log10(rms / (rms.max() + 1e-12) + 1e-12)
    act = np.where(db > floor_db)[0]
    return act[0] * hop, (act[-1] + 1) * hop


def iois(onsets, speech_end):
    return [b - a for a, b in zip(onsets, list(onsets[1:]) + [speech_end])]
