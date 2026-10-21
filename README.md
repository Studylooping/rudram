# Rudram — svara-faithful Mahānyāsa-pūrvaka Rudra recitation

Goal: a learning-reference audio recitation of the Mahānyāsa-pūrvaka Śrī Rudra (Mahānyāsa, then
Śrī Rudra Praśna / Namaka, Taittirīya Saṃhitā 4.5, and Camaka, TS 4.7) in which every syllable
follows the Vedic recitation rules — svara (anudātta / udātta-pracaya / svarita) as pitch and
mātrā as duration — with an automatic per-phrase verification report.

- `TEXT.md` — sources (pinned by sha256, downloaded by script, not stored here), the three-source
  svara cross-check, corrections and unresolved disagreements, Mahānyāsa recension.
- `RULES.md` — the svara → pitch and mātrā model, with citations (Taittirīya Prātiśākhya,
  Pāṇini, present-day practice) and the conventions chosen where sources disagree.
- `audio/` — published mp3s, `audio/README.md` compliance table, `audio/reports/*.json`
  (per-syllable duration and pitch errors).

## Pipeline
1. `python -m rudram.fetch` downloads and verifies the sources; `python -m rudram.crosscheck`
   compares the svaras of the recited text with vedamantra-book and the KYVeda TS 4 text.
2. `python -m rudram.corpus` lists the recitation units (phrases between dandas; over-long
   stretches split at word boundaries).
3. `python -m rudram.audio.recite --section pilot` renders, for every phrase:
   - synthesis with Indic Parler-TTS (male voice "Aryan"; needs `HF_TOKEN`, the model is gated);
   - forced alignment of syllables (torchaudio MMS_FA), time-stretch so that each syllable lasts
     its mātrā target (Rubber Band R3, formants preserved);
   - per-syllable pitch shift to its svara level (Rubber Band pitch scaling, formants preserved),
     iterated on the measured residual;
   - **verification on the final audio**: re-alignment (each syllable within ±20 % of its target)
     and pYIN F0 (each syllable within ±0.5 semitone of its svara level). A failing phrase is
     re-synthesised with other seeds and, if it still fails, reported as non-compliant.
   Phrases are cached in `out/phrases/`, so an interrupted run resumes.
4. `python -m rudram.audio.publish --sections pilot` encodes the mp3, copies the report, rebuilds
   the table and pushes.

The duration machinery (TTS → MMS_FA → Rubber Band → re-alignment check) is adapted from the
sister project [Studylooping/Chandi](https://github.com/Studylooping/Chandi), which recites the
Durgā Saptaśatī by classical chandas; pitch control and pitch verification are new here.

## Setup
`scripts/setup_render.sh` creates a CPU virtualenv (`~/rudram-venv`) and downloads the aligner
checkpoint. Tests: `python -m pytest tests`.

## Limitations
A TTS voice with pitch shifting approximates a trained Vedic reciter. Verified svara pitch and
mātrā timing do not guarantee correct pronunciation. See RULES.md §7.
