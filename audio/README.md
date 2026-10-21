# Recitation audio

Voice: AI4Bharat Indic Parler-TTS (speaker "Aryan"), time-stretched per syllable (Rubber Band
R3, formants preserved) and pitch-set per syllable (WORLD vocoder, spectral envelope kept).
Tempo 1 mātrā = 0.125 s. Rules: `../RULES.md`.

A phrase is **compliant** only if, measured on the final audio, every syllable is within ±20 %
of its mātrā target (forced re-alignment) *and* within ±0.5 semitone of its svara level
(pYIN F0: anudātta −2, udātta/pracaya 0, svarita +1 semitone re 120 Hz). Per-syllable numbers
are in `reports/<section>.json`. The check covers timing and pitch only, **not pronunciation**;
a TTS voice is an approximation of a trained Vedic reciter.

| File | Length | Phrases compliant | Durations ok | Pitch ok | Syllables: duration ok | Syllables: pitch ok | Non-compliant phrases (unit/phrase) |
|---|---|---|---|---|---|---|---|
| [00_PILOT_Dhyana-Namaka-anuvaka-1.mp3](00_PILOT_Dhyana-Namaka-anuvaka-1.mp3) | 3.4 min | 38/40 | 38/40 | 40/40 | 736/738 | 738/738 | dhyana-2/2, namaka-1/14 |

![namaka-1_phrase-1](figures/namaka-1_phrase-1.png)
