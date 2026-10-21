"""Recitation units: each unit is a list of phrases (rendered one TTS call each) with pauses.

  python -m rudram.corpus      -> prints the units with syllable / phrase counts

Unit kinds
  svara : Vedic text with svara marks; every syllable gets a pitch level and a mAtrA target.
  metre : classical verse without svara (the dhyAna zlokas); laghu 1 / guru 2 mAtrAs as in the
          Chandi project, pAda-final syllable held as guru, all syllables at the mid (ekazruti) level.
"""
import re

from rudram import fetch
from rudram.itrans import syllabify

MAX_SYL = 34  # longer danda-delimited stretches are split at a word boundary for the TTS voice
PAUSE = {'phrase': 2, 'danda': 4, 'double': 6, 'unit': 10}  # in mAtrAs (convention, RULES.md 5)

# classical metres of the dhyAna verses (pattern, final syllable anceps)
METRES = {'shArdUlavikrIDita': 'GGGLLGLGLLLGGGLGGLG', 'sragdharA': 'GGGGLGGLLLLLLGGLGGLGG'}


def weights(syls):
    """Classical laghu / guru of each syllable (long vowel, anusvAra / visarga, or two or more
    consonants before the next vowel)."""
    return ''.join('G' if s.matra >= 2 or s.post >= 2 or any(c in ('M', 'H', 'gm') for c in s.coda)
                   else 'L' for s in syls)


def _split_long(phrase):
    """Split an over-long phrase at word boundaries into pieces of at most MAX_SYL syllables,
    preferring a break before a word beginning with nam- (namo / namaH series)."""
    syls, _ = syllabify(phrase)
    if len(syls) <= MAX_SYL:
        return [phrase]
    words = phrase.split()
    counts = [len(syllabify(w)[0]) for w in words]
    total, best = sum(counts), None
    acc = 0
    for k in range(1, len(words)):
        acc += counts[k - 1]
        score = abs(acc - total / 2) - (6 if words[k].startswith('nam') else 0)
        if best is None or score < best[0]:
            best = (score, k)
    k = best[1]
    return _split_long(' '.join(words[:k])) + _split_long(' '.join(words[k:]))


def svara_phrases(text):
    """ITRANS passage -> [(phrase, pause_after)] split at | and ||."""
    out = []
    parts = re.split(r'(\|\||\|)', text)
    for k in range(0, len(parts), 2):
        ph = ' '.join(parts[k].split())
        if not ph:
            continue
        sep = parts[k + 1] if k + 1 < len(parts) else '||'
        pieces = _split_long(ph)
        for j, p in enumerate(pieces):
            last = j == len(pieces) - 1
            out.append((p, ('double' if sep == '||' else 'danda') if last else 'phrase'))
    return out


def metre_phrases(verse, metre):
    """Classical verse (ITRANS, no svara) -> its four pAdas [(pAda, pause_after)]."""
    n = len(METRES[metre])
    text = ' '.join(verse.replace('|', ' ').split())
    syls, _ = syllabify(text)
    if len(syls) != 4 * n:
        raise ValueError(f'{metre}: {len(syls)} syllables, expected {4 * n}: {text[:40]}')
    # cut the ITRANS string at syllable boundaries (inside words where sandhi joins the pAdas)
    pieces, words = [], text.split()
    for w in words:
        pieces += [(w, len(syllabify(w)[0]))]
    padas, cur, cnt = [], [], 0
    for w, c in pieces:
        cur.append(w); cnt += c
        if cnt >= n * (len(padas) + 1):
            padas.append(' '.join(cur)); cur = []
    if cur:
        padas.append(' '.join(cur))
    if len(padas) != 4 or any(len(syllabify(p)[0]) != n for p in padas):
        # a pAda boundary inside a word: fall back to splitting the syllable list
        return [(text, 'double')], True
    return [(p, 'danda' if i % 2 == 0 else 'double') for i, p in enumerate(padas)], False


def namaka_units(src=None):
    s = fetch.section_itrans(src)
    n = s['namaka']
    units = []
    head, rest = n.split('||', 1)
    units.append({'id': 'namaka-0', 'title': 'namo bhagavate rudrAya', 'kind': 'svara',
                  'phrases': svara_phrases(head + '||')})
    chunks = re.split(r'\|\|\s*(\d+)\s*\|\|', rest)
    # chunks: text1, '1', text2, '2', ... text11, '11', tail
    for k in range(0, len(chunks) - 1, 2):
        body, num = chunks[k], int(chunks[k + 1])
        pre = None
        if num == 2:  # the shambhave insertion recited after anuvAka 1 ends with "nama'H ||"
            pre, body = body.split('||', 1)
            units.append({'id': 'namaka-1-shambhave', 'title': 'zambhave namaH (insertion after anuvAka 1)',
                          'kind': 'svara', 'phrases': svara_phrases(pre + '||')})
        units.append({'id': f'namaka-{num}', 'title': f'Namaka anuvAka {num}', 'kind': 'svara',
                      'phrases': svara_phrases(body + '||')})
    units.append({'id': 'namaka-tail', 'title': 'Namaka closing mantras', 'kind': 'svara',
                  'phrases': svara_phrases(chunks[-1])})
    # anuvAka 1 must precede the insertion
    order = ['namaka-0', 'namaka-1', 'namaka-1-shambhave'] + [f'namaka-{i}' for i in range(2, 12)] + ['namaka-tail']
    by = {u['id']: u for u in units}
    return [by[i] for i in order]


def dhyana_units(src=None):
    r = fetch.section_itrans(src)['rudra_file']
    body = r[r.index('\\section{|| dhyAnam ||}') + len('\\section{|| dhyAnam ||}'):]
    body = body[: body.index('shrI\\` gu')]
    chunks = [v for v in body.split('||') if v.strip()]
    verses, metres, cur = [], ['shArdUlavikrIDita', 'sragdharA'], ''
    for c in chunks:  # the second verse also has || after its first half
        cur += ' ' + c
        if len(syllabify(' '.join(cur.replace('|', ' ').split()))[0]) >= 4 * len(METRES[metres[len(verses)]]):
            verses.append(cur); cur = ''
    units = []
    for i, (v, m) in enumerate(zip(verses, ['shArdUlavikrIDita', 'sragdharA'])):
        phrases, fallback = metre_phrases(v, m)
        units.append({'id': f'dhyana-{i + 1}', 'title': f'dhyAna zloka {i + 1} ({m})', 'kind': 'metre',
                      'metre': m, 'phrases': phrases})
    return units


SECTIONS = {
    'pilot': lambda: dhyana_units() + namaka_units()[:3],
    'namaka': lambda: dhyana_units() + namaka_units(),
}


if __name__ == '__main__':
    for name, f in SECTIONS.items():
        print('==', name)
        for u in f():
            n = sum(len(syllabify(p)[0]) for p, _ in u['phrases'])
            print(f"{u['id']:22s} {u['kind']:6s} {len(u['phrases']):3d} phrases {n:5d} syllables")
