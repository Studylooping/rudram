# Source texts and svara cross-check

None of the texts is stored in this repository: their terms do not allow reposting
(sanskritdocuments.org: "not to be copied or reposted for promotion of any website or individuals
or for commercial purpose without permission"; vedamantra-book README: "For personal study use;
not for commercial printing or distribution"; KYVeda/texts states no licence). `python -m
rudram.fetch` downloads them into `data/` and refuses any file whose sha256 differs from the
revision checked here.

| key | file | role | sha256 |
|---|---|---|---|
| `sd_rudra` | sanskritdocuments.org `doc_veda/rudra.itx` — *rudraprashnaH svara sahitam*, Rajagopal Iyer & Rekha Venkatesh, "Latest update … August 29, 2024" | **recited text** (Namaka with laghunyāsa, dhyāna, closing mantras) | `d8c1f9fb…eea1290`… see `rudram/fetch.py` |
| `sd_chamaka` | sanskritdocuments.org `doc_veda/chamaka.itx` — *chamakaprashnaH with vedic accents*, same encoders, "March 19, 2022" | **recited text** (Camaka) | pinned in `rudram/fetch.py` |
| `vmb_*` | github.com/stotrasamhita/vedamantra-book @ `3bbc26b6`, `mantras/RudraPrashnah.tex`, `ChamakaPrashnah.tex`, `MahaNyasah.tex` (Unicode Devanagari with svaras) | cross-check; **Mahānyāsa text** | pinned |
| `kyveda_ts4` | github.com/KYVeda/texts @ `76fe735a`, `saMhitA/04/TS 4 Baraha.BRH` (Taittirīya Saṃhitā kāṇḍa 4, Baraha ASCII, svaras `q` anudātta, `#` svarita, `$` dīrgha-svarita) | independent cross-check against the Saṃhitā | pinned |

Not usable / not reachable from the build environment (checked 21 Oct 2026): sanskritdocuments
`taittirIyasamhitA.itx` (TS 4.5 there is unaccented), TITUS (HTTP 503), GRETIL (links to TITUS for
the TS), vignanam.org and vedavms.in (403), archive.org (connection reset), sa.wikisource (429).

**Independence.** vedamantra-book credits sanskritdocuments.org and sa.wikisource as sources, so
it is *not* clearly independent of the recited text; KYVeda (Vedavms volunteer group, a guess
from a file in that repository) is a separately encoded Saṃhitā text and is the meaningful check.

## Method
`python -m rudram.crosscheck` converts all three to the same svara-ITRANS, syllabifies them with
the recitation parser, aligns the syllable sequences (difflib, svara ignored) and lists every
aligned syllable whose svara differs. Unaligned stretches are textual differences (recitation
insertions such as the *śambhave namaḥ* passage and the closing mantras, which are not in TS 4.5
/ 4.7; sandhi and spelling variants) and are **not svara-checked** by the Saṃhitā.

## Result (after the corrections below)
| part | reference | our syllables | aligned | svara disagreements |
|---|---|---|---|---|
| Namaka | vedamantra-book | 3234 | 3223 | 1 |
| Namaka | KYVeda TS 4.5 | 3234 | 2903 | 2 (one word) |
| Camaka | vedamantra-book | 1826 | 1821 | 0 |
| Camaka | KYVeda TS 4.7.1–11 | 1826 | 1716 | 0 |

### Corrections made (`CORRECTIONS` in `rudram/fetch.py`) — both references agree against the primary text
1. Camaka 1 (TS 4.7.1): primary *varma' cha me`.a~NgA'ni* → *varma' cha` me.a~NgA'ni*
   (vedamantra-book वर्म॑ च॒ मेऽङ्गा॑नि; KYVeda `varma# caq mE &~ggA#ni`).
2. Camaka 5 (TS 4.7.5): primary *vi`ttaM cha me`* → *vi`ttaM cha' me`*
   (vedamantra-book वि॒त्तं च॑ मे॒; KYVeda `viqttaM ca# mEq`).

A parser fix found the same way: in *ahIg'shcha*, *janAn'*, *sharI'ra`g`M* the mark written
after a coda consonant belongs to the preceding vowel (both references mark अहीꣳ॑श्च).

### Unresolved (primary text kept)
1. Namaka 1 *adṛśann adṛśan*: primary and KYVeda अ॑दृश॒न्नदृ॑शन् (न unmarked); vedamantra-book
   अ॑दृश॒न्न॒दृ॑शन् (न॒ anudātta). 2 of 3 sources agree with the primary text.
2. Namaka 11 *kapardinaḥ*: primary and vedamantra-book कप॒र्दिनः॑; KYVeda कप॒र्दि॑नः
   (`kapaqrdi#naH`). Not decidable from these sources; the primary reading is kept.

## Mahānyāsa recension
The Mahānyāsa recited before the Rudra in the South-Indian tradition is the *Bodhāyana*
framework (Bodhāyana gṛhya-śeṣa-sūtra; KYVeda/texts `Shiva-Stuti/Mahanyasa Sutrani -
Sanskrit.BRH` cites "Bhodhayna gruhya SeSha sutraM - 6.9" and the R. S. Vadhyaar & Sons,
Kalpathi edition) with prayer verses attributed to Rāvaṇa for the pañcāṅga and pañcamukha
nyāsas ("रावणोक्ता पञ्चाङ्गप्रार्थना", section headings of vedamantra-book `MahaNyasah.tex`).
The svara-marked text used is vedamantra-book `MahaNyasah.tex` (not yet cross-checked; to be done
before its render).
