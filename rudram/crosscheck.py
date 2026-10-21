"""Cross-check the svaras of the recited text against independent svara-marked sources.

  python -m rudram.crosscheck            -> data/crosscheck_<part>.json + summary on stdout

Every source is converted to the same svara-ITRANS notation and syllabified with
rudram.itrans; the syllable sequences (onset + vowel, svara ignored) are aligned with difflib
and every aligned syllable whose svara differs is recorded. Text differences (sandhi, spelling,
recitation-only insertions) appear as unaligned stretches and are counted separately.
"""
import difflib
import json
import re

from rudram import fetch
from rudram.itrans import PITCH, ROM_CONS, ROM_VOWEL, syllabify

# ------------------------------------------------------------------ Devanagari (Unicode) -> ITRANS
_DCONS = {'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': '~N', 'च': 'ch', 'छ': 'Ch', 'ज': 'j',
          'झ': 'jh', 'ञ': '~n', 'ट': 'T', 'ठ': 'Th', 'ड': 'D', 'ढ': 'Dh', 'ण': 'N', 'त': 't',
          'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n', 'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh',
          'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'Sh', 'स': 's',
          'ह': 'h', 'ळ': 'L'}
_DIND = {'अ': 'a', 'आ': 'A', 'इ': 'i', 'ई': 'I', 'उ': 'u', 'ऊ': 'U', 'ऋ': 'R^i', 'ॠ': 'R^I',
         'ऌ': 'L^i', 'ॡ': 'L^I', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'}
_DSIGN = {'ा': 'A', 'ि': 'i', 'ी': 'I', 'ु': 'u', 'ू': 'U', 'ृ': 'R^i', 'ॄ': 'R^I', 'ॢ': 'L^i', 'ॣ': 'L^I',
          'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au'}
_DMARK = {'ं': 'M', 'ः': 'H', 'ꣳ': '{\\m+}', 'ꣴ': '{\\m+}', '॒': '\\`', '॑': "\\'", '᳚': '\\"',
          'ऽ': '.a', 'ॐ': 'OM', '्': ''}


def dev_to_itrans(text):
    out = []
    for k, c in enumerate(text):
        if c in _DCONS:
            nxt = text[k + 1] if k + 1 < len(text) else ''
            # an inherent a unless a vowel sign / virama follows (svara marks may come first)
            j = k + 1
            while j < len(text) and text[j] in '॒॑᳚':
                j += 1
            nxt = text[j] if j < len(text) else ''
            out.append(_DCONS[c] + ('' if nxt in _DSIGN or nxt == '्' else 'a'))
        elif c in _DIND:
            out.append(_DIND[c])
        elif c in _DSIGN:
            out.append(_DSIGN[c])
        elif c in _DMARK:
            out.append(_DMARK[c])
        elif c in '।॥|':
            out.append(' | ')
        elif c in ' \n\t-':
            out.append(' ')
        elif c == '\u200c' or '०' <= c <= '९' or c.isdigit():
            pass
        else:
            out.append(' ')
    return ''.join(out)


def tex_body(tex):
    tex = re.sub(r'%.*', '', tex)
    tex = re.sub(r'\\(chapt|section|newpage|textbf|centering|begin|end)\*?(\{[^}]*\})?', ' ', tex)
    return tex.replace('\\-', '').replace('\\\\', ' ').replace('{', ' ').replace('}', ' ')


# ------------------------------------------------------------------ Baraha (ASCII) -> ITRANS
_BARAHA = [('(gm)', '{\\m+}'), ('(gg)', '{\\m+}'), ('^^', ''), ('qq', '\\`'), ('q', '\\`'), ('#', "\\'"),
           ('$', '\\"'), ('&&*', '.a'), ('&&', '.a'), ('&*', '.a'), ('&', '.a'), ('~M', 'M'), ('~g', '~N'), ('~j', '~n'), ('Sh', 'Sh'), ('S', 'sh'),
           ('Ru', 'R^i'), ('RU', 'R^I'), ('K', 'kh'), ('G', 'gh'), ('C', 'Ch'), ('J', 'jh'), ('P', 'ph'),
           ('B', 'bh'), ('E', 'e'), ('O', 'o'), ('c', 'ch')]
_BRE = re.compile('|'.join(re.escape(a) for a, _ in _BARAHA))


def baraha_to_itrans(text):
    text = re.sub(r'\([^)]*\)', ' ', text.replace('(gm)', '\0').replace('(gg)', '\1'))
    text = text.replace('\0', '(gm)').replace('\1', '(gg)')
    text = re.sub(r'\[[^\]]*\]\s*\d*', ' ', text)
    text = re.sub(r'\d+', ' ', text).replace('.', '')
    return _BRE.sub(lambda m: dict(_BARAHA)[m.group(0)], text)


def baraha_ts(text, prefix, last_anuvaka=99):
    """Saṃhitā lines of every 'TS <prefix>.n.m' block (n <= last_anuvaka), in order."""
    out, on = [], False
    for ln in text.splitlines():
        if ln.startswith('TS '):
            ref = ln.split()[1]
            on = ref.startswith(prefix + '.') and int(ref.split('.')[2]) <= last_anuvaka
            continue
        if any(w in ln for w in ('Anuvaa', 'Padam', 'fOr ', ' Of ', 'KOrvai')):
            on = False
        if ln.startswith('===') or ln.startswith('Appearing') or ln.startswith('(Appearing'):
            on = False
        if on and ln.strip() and not ln.lstrip().startswith('(') and ':' not in ln and ',' not in ln:
            out.append(ln)
    return baraha_to_itrans('\n'.join(out))


# ------------------------------------------------------------------ comparison
def seq(itrans_text):
    """[(key, svara, context)] for every syllable; key = onset + vowel (romanised)."""
    out = []
    for ph in re.split(r'\|+', itrans_text):
        if not ph.strip():
            continue
        syls, _ = syllabify(ph.strip())
        for k, s in enumerate(syls):
            key = ''.join(ROM_CONS[c] for c in s.onset[-1:]) + ROM_VOWEL[s.vowel]
            ctx = ''.join(x.dev(True) for x in syls[max(0, k - 3): k + 3])
            out.append((key, s.svara, ctx, s.dev(True)))
    return out


def compare(a, b):
    """Align syllable sequences a (recited text) and b (reference); return stats + disagreements."""
    sm = difflib.SequenceMatcher(a=[x[0] for x in a], b=[x[0] for x in b], autojunk=False)
    aligned, diffs = 0, []
    for blk in sm.get_matching_blocks():
        for i in range(blk.size):
            x, y = a[blk.a + i], b[blk.b + i]
            aligned += 1
            if x[1] != y[1]:
                diffs.append({'pos': blk.a + i, 'syllable': x[3], 'ours': x[1], 'ref': y[1],
                              'pitch_class_differs': PITCH[x[1]] != PITCH[y[1]],
                              'ours_ctx': x[2], 'ref_ctx': y[2]})
    return {'syllables_ours': len(a), 'syllables_ref': len(b), 'aligned': aligned,
            'svara_disagreements': len(diffs),
            'pitch_class_disagreements': sum(d['pitch_class_differs'] for d in diffs), 'diffs': diffs}


def main():
    src = fetch.fetch_all()
    ours = fetch.section_itrans(src)
    out = {}
    vmb_r = dev_to_itrans(tex_body(src['vmb_rudra'].read_text(encoding='utf-8')))
    vmb_c = dev_to_itrans(tex_body(src['vmb_chamaka'].read_text(encoding='utf-8')))
    brh = src['kyveda_ts4'].read_text(encoding='latin-1')
    refs = {'namaka': {'vedamantra-book': vmb_r, 'KYVeda TS 4.5': baraha_ts(brh, '4.5')},
            'chamaka': {'vedamantra-book': vmb_c, 'KYVeda TS 4.7': baraha_ts(brh, '4.7', 11)}}
    for part, rs in refs.items():
        a = seq(ours[part])
        out[part] = {name: compare(a, seq(t)) for name, t in rs.items()}
        for name, r in out[part].items():
            print(f"{part} vs {name}: {r['aligned']}/{r['syllables_ours']} syllables aligned, "
                  f"{r['svara_disagreements']} svara disagreements ({r['pitch_class_disagreements']} change the pitch class)")
    path = fetch.DATA / 'crosscheck.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
