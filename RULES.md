# Recitation rules implemented

This file states the svara-to-pitch and mātrā model that `rudram/audio/render.py` implements,
with the sources it rests on. Where sources disagree, the disagreement is listed and the
convention chosen is named. Quotations from the Taittirīya Prātiśākhya (TPr) are W. D. Whitney's
English translation (JAOS 9, 1871; Whitney's sūtra numbering), read in the proofread
transcription by Ramesh Srinivasan (2005), <http://sanskritweb.net/yajurveda/tp-comb.pdf>
(the Sanskrit there uses a legacy font that does not extract cleanly, so the Sanskrit wording
is not quoted from it). Pāṇini's sūtras are from the ashtadhyayi.com data file,
<https://raw.githubusercontent.com/ashtadhyayi-com/data/master/sutraani/data.txt>.

Items marked **UNVERIFIED** could not be checked against a source and are conventions of this
project.

## 1. The svara marks of the text

The recited text (see `TEXT.md`) uses the Taittirīya marking convention: anudātta = stroke
below (U+0952, ITRANS `` \` ``), svarita = stroke above (U+0951, `\'`), dīrgha-svarita = double
stroke above (U+1CDA, `\"`); udātta and pracaya are **unmarked**.
- Arsha Vidya, *Rules of chanting*: "Udätta is left unmarked; the anudätta is marked with a
  horizontal line underneath … svarita is a perpendicular stroke above"
  (<https://arshadrishti.org/wp-content/uploads/2016/04/Rules-of-Chanting-in-Samskritam.pdf>).
- Unicode NamesList: "1CDA VEDIC TONE DOUBLE SVARITA = vaidika svarita uurdhva dvi rekhaa",
  under "Signs for Yajurvedic" (<https://www.unicode.org/Public/UCD/latest/ucd/NamesList.txt>);
  L2/09-344: "the dirgha svarita (a special kind of svarita), which is marked in Devanagari by
  the double upper stroke 1CDA" (<https://www.unicode.org/L2/L2009/09344-candra-above.pdf>).

## 2. Svara → pitch

### What the śāstra says
- TPr 1.38–1.40: "A syllable uttered in a high tone is acute." / "In a low tone, grave." /
  "Their combination is circumflex." Pāṇini 1.2.29–31: उच्चैरुदात्तः । नीचैरनुदात्तः । समाहारः स्वरितः ।
- Svarita shape: Pāṇini 1.2.32 तस्यादित उदात्तमर्धह्रस्वम् (its first half-short-vowel is udātta).
  TPr 1.41–1.47 lists competing views: "the first part, to the extent of half a short vowel, is
  uttered in a yet higher tone" (1.41), "The remainder has the same tone with acute" (1.42),
  "Or the part following is uttered in a lower tone" (1.44), "Or in the same tone with grave"
  (1.45), "Its beginning is the same with acute; its remainder is the same with grave: so say the
  teachers" (1.46), "It is all a slide, say some" (1.47).
- Pracaya: TPr 21.10 "Of grave syllables following a circumflex in saṃhitā there is pracaya,
  having the tone of acute." 21.11 "But not when an acute or circumflex follows."
  Pāṇini 1.2.39 स्वरितात् संहितायामनुदात्तानाम् (ekaśruti after a svarita).
- Pāṇini 1.2.40 उदात्तस्वरितपरस्य सन्नतरः (an anudātta before an udātta or svarita is *sannatara*,
  "lower"); the TPr has no such rule (it only blocks pracaya there, 21.11).

### What present-day Taittirīya recitation does
In the living South-Indian Kṛṣṇa-Yajurveda tradition the svarita is the **highest** note, the
udātta the middle (the reciter's normal pitch) and the anudātta the lowest:
- Vedavms, *Basics of Veda Swaras*
  (<https://vedavms.in/docs/articles/01Basics%20of%20Veda%20Swaras.pdf>): udātta "rendered in
  the normal pitch note in one's voice … An UdAtta akshara is left unmarked"; svarita "rendered
  in the upper note compared to UdAtta"; "UdAtta is rendered in the swaram of Nishada … or
  Gandhara … AnudAtta … Dhaivata … or Rishaba … Swarita … Sadja … Madhyama … or Panchama".
- Wikipedia, *Vedic chant*: "udātta … (middle tone), anudātta … (lower tone), svarita … (higher
  tone) and dīrgha svarita … (high tone extended)" (<https://en.wikipedia.org/wiki/Vedic_chant>).
- A practitioner's account on the Advaita-L list says that in current practice "the *entire
  syllable* … is at a higher tone than the udAtta in case of the hrasva svarita"
  (<https://www.advaita-vedanta.org/archives/advaita-l/2009-February/021304.html>).

### Disagreements
1. *Which tone is highest*: Pāṇini/TPr call the udātta "high"; modern Taittirīya practice
   (above) sings the svarita highest.
2. *Pracaya*: TPr 21.10 = udātta pitch; Vedavms puts ekaśruti "lower than udAtta"; the
   Advaita-L post "slightly (ever so slightly) higher than udAtta in current practice".
3. *Svarita contour*: five options in TPr 1.41–47; current practice = a level high syllable.
4. *Sannatara*: Pāṇini 1.2.40 lowers it; Vedavms recites it "lower than anudAtta"; the TPr is
   silent and the Taittirīya marking does not distinguish it from other anudāttas.

### Convention implemented (three levels)
| class | syllables | level |
|---|---|---|
| low | every marked anudātta (incl. sannatara) | −2 semitones |
| mid | unmarked: udātta and pracaya (TPr 21.10) | 0 (base, `BASE_HZ` = 120 Hz) |
| high | svarita and dīrgha-svarita | +1 semitone |

The intervals follow the Vedavms note mapping Dha / Ni / Sa (and Ri / Ga / Ma): anudātta →
udātta about a whole tone, udātta → svarita about a semitone. That numerical reading of the
note names is this project's inference (**UNVERIFIED** against acoustic measurement; no
acoustic study of Taittirīya recitation was found. J. E. B. Gray, BSOAS 22, 1959, measured
Ṛgvedic recitation, reported as "low-tone was nearly always a minor third below mid-tone";
that wording could not be checked).
The svarita is realised as a level high syllable (current practice), not as a contour; sannatara
is not lowered further; kampa is not rendered (see 3).

## 3. Dīrgha-svarita and kampa
The dīrgha-svarita gets the high level like the svarita. Vedavms says it is "rendered in the upper
note like Swarita for twice the time (MAtra) scale"; Arsha Vidya: it occurs "at the end of a
sentence, or in the middle of the word on a dirgha svara followed by a conjunct consonant".
In the recited text every dīrgha-svarita stands on a long vowel, which already lasts 2 mātrās,
so this engine gives it its vowel's length and no extra mātrā (**convention**; "twice the time"
could also mean an added mātrā). Kampa (Vedavms describes a "Kampa Swara" for successive
dīrgha-svarita + svarita) is **not** rendered.

## 4. Mātrā (duration) model
- TPr 1.35–1.36: "An element of twice that quantity is long." / "… three times that quantity is
  protracted." (Pāṇini 1.2.27 ऊकालोऽज्झ्रस्वदीर्घप्लुतः.) → hrasva 1, dīrgha 2, pluta 3
  (pluta is written with the numeral 3, e.g. *o3m*).
- TPr 1.37: "A consonant has half the quantity of a short vowel." → ½ mātrā per consonant.
- TPr 1.34 "Also anusvāra" (among the one-unit elements) and 17.5 "And to the vowel is added,
  in this case, the time of a consonant." → anusvāra counted as one consonant (½).
- Visarga: **UNVERIFIED** (no TPr rule found); counted as one consonant (½).
- Taittirīya anusvāra before r / ś ṣ s h (ꣳ, "gum"): TPr 13.2 / 15.1 / 15.3 describe the loss of
  m and nasalisation; the [g] is described by Shriramana Sharma
  (<http://www.sanskritweb.net/sansdocs/anusvara.pdf>): "takes a voiced velar stop [g] before it
  (and a [ɨ̆] in between to ease the transition), thus rendering the pronunciation [g ɨ̆ṃ]".
  Implemented: the voice is given गुं, and the sound counts as two consonants ([g] + [ṃ], 1 mātrā).
  Sharma's variants (no āgama-anusvāra; [gg ɨ̆] after a short vowel before a cluster) are not
  rendered.
- Svarabhakti (TPr 21.15 "In the combination of r and a spirant, there is a svarabhakti of r"):
  **not modelled** (its length is unverified); a svara mark written on such an r is ignored.
- Avagraha (ऽ) marks an elided *a*: no syllable, no time.

**Timing unit.** As in the Chandi project a syllable's duration is measured from its vowel onset
to the next vowel onset. The target for each syllable is

    vowel mātrās + ½ × (number of consonant sounds after the vowel up to the next vowel)

e.g. *na-ma-* 1 + ½ = 1.5; *bā-hu-* 2 + ½ = 2.5; *ru-dra* (ru + d r) 1 + 1 = 2. The phrase-final
syllable runs to the end of speech. Default tempo: 1 mātrā = 0.125 s.

Dhyāna ślokas (classical verse, no svaras) are timed by classical weight instead, as in the
Chandi project: laghu 1, guru 2, pāda-final syllable held as guru, all syllables on the mid level.

## 5. Pauses (project convention, not from the sources)
2 mātrās where a long passage is split for the voice, 4 at `|`, 6 at `||`, 10 between units.

## 6. Verification (what "compliant" means)
A phrase is reported compliant only if, measured on the final audio:
- **durations**: after re-alignment (MMS_FA forced alignment) every syllable is within ±20 % of
  its target × the fitted unit (as in Chandi);
- **pitch**: every syllable's median F0 (pYIN, voiced frames from its vowel onset to the next
  syllable's onset consonants) is within ±0.5 semitone of its class level, so that the nearest
  level is the right class. A syllable whose F0 cannot be measured counts as a failure.
A failing phrase is re-synthesised with other seeds; if none passes, the best take is used and
reported as non-compliant.

## 7. What this does not guarantee
A TTS voice with pitch-shifting is an approximation of a trained Vedic reciter. Correct svara
levels and mātrā timing do not guarantee correct pronunciation (the voice was trained on modern
speech and may mispronounce Vedic sounds, e.g. ḷ, visarga echo, svarabhakti, the gum anusvāra),
and the svarita/udātta interval of one semitone is a convention chosen from a practitioner source.
