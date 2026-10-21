"""Parse svara-marked ITRANS (sanskritdocuments.org Vedic convention) into syllables.

Marks (Taittiriya convention, as used in the source files): \\` anudatta (stroke below),
\\' svarita (stroke above), \\" dirgha-svarita (double stroke above); udatta and pracaya
are unmarked. A mark follows the vowel it belongs to (possibly after M / H / {\\m+}).
A mark written after a vowel-less consonant (e.g. va\\`r__\\`Sham, rendered व॒र्॒षम्) belongs to
the svarabhakti of that r, which this engine does not model: it is recorded and ignored.

Syllabification: every vowel is the nucleus of one syllable. Consonants between two vowels
form the onset of the following syllable (for alignment); anusvara / visarga and consonants
at the end of a phrase are the coda of the preceding syllable. `post` counts all consonant
sounds after the vowel up to the next vowel (anusvara, visarga, cluster), which the duration
model uses (see RULES.md).
"""
import dataclasses
import re

VOWELS = [  # (itrans, code, matra)
    ('R^I', 'RR', 2), ('RRI', 'RR', 2), ('R^i', 'R', 1), ('RRi', 'R', 1), ('L^I', 'LRR', 2), ('L^i', 'LR', 1),
    ('aa', 'A', 2), ('ai', 'ai', 2), ('au', 'au', 2), ('ii', 'I', 2), ('uu', 'U', 2),
    ('A', 'A', 2), ('I', 'I', 2), ('U', 'U', 2), ('a', 'a', 1), ('i', 'i', 1), ('u', 'u', 1),
    ('e', 'e', 2), ('o', 'o', 2),
]
# itrans -> list of phonemes (code); ksha and j~na are two consonants each
CONSONANTS = [
    ('kSh', ['k', 'Sh']), ('j~n', ['j', '~n']), ('GY', ['j', '~n']), ('chh', ['Ch']),
    ('kh', ['kh']), ('gh', ['gh']), ('~N', ['~N']), ('Ch', ['Ch']), ('ch', ['ch']), ('jh', ['jh']),
    ('~n', ['~n']), ('Th', ['Th']), ('Dh', ['Dh']), ('th', ['th']), ('dh', ['dh']), ('ph', ['ph']),
    ('bh', ['bh']), ('sh', ['sh']), ('Sh', ['Sh']), ('x', ['k', 'Sh']),
    ('k', ['k']), ('g', ['g']), ('c', ['ch']), ('j', ['j']), ('T', ['T']), ('D', ['D']), ('N', ['N']),
    ('t', ['t']), ('d', ['d']), ('n', ['n']), ('p', ['p']), ('b', ['b']), ('m', ['m']), ('y', ['y']),
    ('r', ['r']), ('l', ['l']), ('v', ['v']), ('w', ['v']), ('s', ['s']), ('h', ['h']), ('L', ['L']),
]
CODA_MARKS = [('{\\m+}', 'gm'), ('M', 'M'), ('H', 'H'), ('.n', 'M')]
# pitch class realised in recitation (RULES.md): low / mid / high
PITCH = {'A': 'low', 'U': 'mid', 'S': 'high', 'D': 'high'}
SVARA = {'\\`': 'A', "\\'": 'S', '\\"': 'D'}

DEV_CONS = {'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ', '~N': 'ङ', 'ch': 'च', 'Ch': 'छ', 'j': 'ज',
            'jh': 'झ', '~n': 'ञ', 'T': 'ट', 'Th': 'ठ', 'D': 'ड', 'Dh': 'ढ', 'N': 'ण', 't': 'त',
            'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न', 'p': 'प', 'ph': 'फ', 'b': 'ब', 'bh': 'भ',
            'm': 'म', 'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व', 'sh': 'श', 'Sh': 'ष', 's': 'स',
            'h': 'ह', 'L': 'ळ'}
DEV_VOWEL = {'a': ('अ', ''), 'A': ('आ', 'ा'), 'i': ('इ', 'ि'), 'I': ('ई', 'ी'), 'u': ('उ', 'ु'),
             'U': ('ऊ', 'ू'), 'R': ('ऋ', 'ृ'), 'RR': ('ॠ', 'ॄ'), 'LR': ('ऌ', 'ॢ'), 'LRR': ('ॡ', 'ॣ'), 'e': ('ए', 'े'),
             'ai': ('ऐ', 'ै'), 'o': ('ओ', 'ो'), 'au': ('औ', 'ौ')}
DEV_CODA = {'M': 'ं', 'H': 'ः', 'gm': 'ꣳ'}  # U+A8F3 Taittiriya anusvara ("gum")
DEV_SVARA = {'A': '॒', 'S': '॑', 'D': '᳚'}
VIRAMA = '्'
# romanisation for the MMS_FA aligner (its dictionary is lowercase a-z)
ROM_CONS = {'k': 'k', 'kh': 'kh', 'g': 'g', 'gh': 'gh', '~N': 'n', 'ch': 'c', 'Ch': 'ch', 'j': 'j',
            'jh': 'jh', '~n': 'n', 'T': 't', 'Th': 'th', 'D': 'd', 'Dh': 'dh', 'N': 'n', 't': 't',
            'th': 'th', 'd': 'd', 'dh': 'dh', 'n': 'n', 'p': 'p', 'ph': 'ph', 'b': 'b', 'bh': 'bh',
            'm': 'm', 'y': 'y', 'r': 'r', 'l': 'l', 'v': 'v', 'sh': 'sh', 'Sh': 'sh', 's': 's',
            'h': 'h', 'L': 'l'}
ROM_VOWEL = {'a': 'a', 'A': 'aa', 'i': 'i', 'I': 'ii', 'u': 'u', 'U': 'uu', 'R': 'ri', 'RR': 'rii',
             'LR': 'li', 'LRR': 'lii', 'e': 'e', 'ai': 'ai', 'o': 'o', 'au': 'au'}
ROM_CODA = {'M': 'm', 'H': 'h', 'gm': 'gum'}  # recited [gɨ̆M], written गुं for the voice


@dataclasses.dataclass
class Syl:
    onset: list          # consonant phonemes before the vowel
    vowel: str           # vowel code
    matra: int           # 1 hrasva, 2 dirgha, 3 pluta
    svara: str = 'U'     # A anudatta, U unmarked (udatta / pracaya), S svarita, D dirgha-svarita
    coda: list = dataclasses.field(default_factory=list)  # M / H / gm and phrase-final consonants
    word_start: bool = False
    post: float = 0      # consonant sounds after the vowel up to the next vowel
    initial: bool = False  # independent vowel (no onset consonant)
    pre: int = 0         # leading onset consonants that end the previous word (asmAn vR^i-)

    def dev(self, marks=False, skip=0):
        """Devanagari of the syllable; skip leaves out its first `skip` onset consonants."""
        onset = self.onset[skip:]
        s = ''.join(DEV_CONS[c] + VIRAMA for c in onset)
        ind, sign = DEV_VOWEL[self.vowel]
        s = s[:-1] + sign if onset else ind
        if self.matra == 3:
            s += '३'
        mark = DEV_SVARA.get(self.svara, '') if marks else ''
        k = 0
        while k < len(self.coda) and self.coda[k] in DEV_CODA:
            s += DEV_CODA[self.coda[k]]; k += 1
        s += mark
        for c in self.coda[k:]:
            s += DEV_CODA[c] if c in DEV_CODA else DEV_CONS[c] + VIRAMA
        return s

    def rom(self):
        """(onset, vowel, coda) strings for the aligner."""
        return (''.join(ROM_CONS[c] for c in self.onset), ROM_VOWEL[self.vowel],
                ''.join(ROM_CODA[c] if c in ROM_CODA else ROM_CONS[c] for c in self.coda))


def _match(s, i, table):
    for k, v in table:
        if s.startswith(k, i):
            return k, v
    return None, None


def tokenize(text):
    """ITRANS -> tokens: ('C', phoneme) ('V', code, matra) ('K', coda) ('S', svara) ('W',) word
    boundary, ('P',) pluta marker. Unknown characters raise ValueError."""
    toks, i = [], 0
    text = text.replace('OM', 'o{OM}')  # praNava: o + m (written ॐ)
    while i < len(text):
        if text.startswith('{OM}', i):
            toks.append(('C', 'm')); toks.append(('X',)); i += 4; continue
        k, v = _match(text, i, list(SVARA.items()))
        if k:
            toks.append(('S', v)); i += len(k); continue
        if text.startswith('\\-', i) or text.startswith('\\,', i):
            toks.append(('W',)); i += 2; continue
        if text.startswith('.a', i):  # avagraha: elided a, no syllable
            toks.append(('W',)); i += 2; continue
        k, v = _match(text, i, CODA_MARKS)
        if k:
            toks.append(('K', v)); i += len(k); continue
        k, v = _match(text, i, [(a, (b, m)) for a, b, m in VOWELS])
        if k:
            toks.append(('V',) + v); i += len(k); continue
        k, v = _match(text, i, CONSONANTS)
        if k:
            toks += [('C', p) for p in v]; i += len(k); continue
        c = text[i]
        if c == '3' and toks and toks[-1][0] in ('V', 'S'):
            toks.append(('P',))
        elif c.isdigit():
            toks.append(('W',))  # verse / anuvaka numbering
        elif c in ' \t\n-':
            toks.append(('W',))
        elif c == '_':
            pass  # ligature breaker, no sound
        else:
            raise ValueError(f'unknown ITRANS at {i}: {text[max(0, i - 10):i + 10]!r}')
        i += 1
    return toks


def syllabify(text):
    """ITRANS phrase -> (list of Syl, list of ignored-mark notes)."""
    toks = tokenize(text)
    syls, pending, notes, word_start, cut = [], [], [], True, 0
    last = None  # kind of last sounding token
    for t in toks:
        kind = t[0]
        if kind == 'W':
            if pending and not word_start:
                cut = len(pending)  # these consonants close the previous word
            word_start = True
            continue
        if kind == 'X':
            # end of OM: the m is the coda of the o
            syls[-1].coda.append(pending.pop()) if pending else None
            continue
        if kind == 'C':
            pending.append(t[1]); last = 'C'
        elif kind == 'V':
            syls.append(Syl(onset=pending, vowel=t[1], matra=t[2], word_start=word_start or not syls,
                            initial=not pending, pre=cut if syls else 0))
            pending, word_start, last, cut = [], False, 'V', 0
        elif kind == 'P':
            syls[-1].matra = 3
        elif kind == 'K':
            if not syls:
                raise ValueError(f'coda before any vowel: {text!r}')
            if pending:  # e.g. "g{\m+}" never occurs, but a consonant before M stays a coda
                syls[-1].coda += pending; pending = []
            syls[-1].coda.append(t[1]); last = 'K'
        elif kind == 'S':
            if last in ('V', 'K') and not pending:
                syls[-1].svara = t[1]
            elif pending == ['r']:
                # mark on a svarabhakti r (va\\`r__\\`Sham): not modelled
                notes.append(f'svara mark on svarabhakti r ignored: {text[:40]}')
            elif syls:
                # mark written after a coda consonant (ahIg\\'shcha, janAn\\', sharI\\'ra\\`g\\`M):
                # it belongs to the preceding vowel
                if syls[-1].svara != 'U' and syls[-1].svara != t[1]:
                    raise ValueError(f'conflicting svara marks: {text[:60]!r}')
                syls[-1].svara = t[1]
    if pending:
        syls[-1].coda += pending
    # consonant sounds after each vowel up to the next vowel
    for k, s in enumerate(syls):
        nxt = len(syls[k + 1].onset) if k + 1 < len(syls) else 0
        s.post = len(s.coda) + nxt
    return syls, notes


def clean(text):
    """Drop TeX / numbering noise from an ITRANS line, keep dandas."""
    text = re.sub(r'\|\|\s*\d+\s*\|\|', '||', text)
    text = text.replace('##', ' ')
    return text


def devanagari(syls, marks=False, dev=None):
    """Words in Devanagari. A consonant that ends a word but stands in the next syllable's onset
    (asmAn vR^iNaktu) is written with its own word. dev(syl, skip) renders one syllable."""
    dev = dev or (lambda s, skip: s.dev(marks, skip))
    out = []
    for s in syls:
        if s.word_start and out:
            if s.pre:
                out.append(''.join(DEV_CONS[c] + VIRAMA for c in s.onset[:s.pre]))
            out.append(' ')
        out.append(dev(s, s.pre if s.word_start and out else 0))
    return ''.join(out)
