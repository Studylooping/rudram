"""Mahanyasa units from vedamantra-book mantras/MahaNyasah.tex (Unicode Devanagari with svaras).

  python -m rudram.mahanyasa          -> prints the sections and their units

The file is LaTeX: its \\newcommand macros (\\indradi, \\raudri, \\ssankalpa, \\um, ...) are
expanded with their arguments, verse macros (\\twolineshloka etc.) become text with dandas, and
layout / editorial matter is dropped: English body-part labels ({\\scriptsize (EAST)}),
footnotes (alternative readings), (ऋक्) labels, verse numbers. Bracketed text ([...]) is kept
(see TEXT.md). Only the nyasa proper is taken: from the first section to the end of the
aSTAGga-namaskAra section; the laghunyAsa / pUjA sections that follow in the file are not part
of the Mahanyasa recitation.
"""
import re

from rudram import fetch
from rudram.crosscheck import dev_to_itrans
from rudram.corpus import svara_phrases
from rudram.itrans import syllabify

LAST_SECTION = 'अष्टाङ्ग-नमस्काराः'


def _args(s, i, n):
    """Read n brace-delimited arguments starting at s[i] (skipping whitespace and %-newlines)."""
    out = []
    for _ in range(n):
        while i < len(s) and s[i] in ' \n\t%':
            if s[i] == '%':
                i = s.index('\n', i)
            i += 1
        if i >= len(s) or s[i] != '{':
            break
        depth, j = 0, i
        while True:
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(s[i + 1:j])
        i = j + 1
    return out, i


def _strip_comments(tex):
    # a % that is not escaped starts a comment up to the end of the line
    return re.sub(r'(?<!\\)%[^\n]*', '', tex)


def expand(tex):
    tex = _strip_comments(tex)
    # collect \newcommand{\name}[n]{body}
    macros = {}
    for m in list(re.finditer(r'\\newcommand\{\\(\w+)\}\[(\d)\]', tex)):
        (body,), _ = _args(tex, m.end(), 1)
        macros[m.group(1)] = (int(m.group(2)), body)
    # remove the definitions themselves
    for name, (n, body) in macros.items():
        start = tex.index('\\newcommand{\\' + name + '}')
        _, end = _args(tex, start + len('\\newcommand{\\' + name + '}') + 3, 1)
        tex = tex[:start] + tex[end:]
    verse = {'twolineshloka': 2, 'threelineshloka': 3, 'fourlineindentedshloka': 4, 'onelineshloka': 1}
    out, i = [], 0
    while i < len(tex):
        m = re.compile(r'\\(\w+)\*?').match(tex, i)
        if not m:
            out.append(tex[i]); i += 1; continue
        name = m.group(1)
        if name in macros:
            n, body = macros[name]
            args, i = _args(tex, m.end(), n)
            args += [''] * (n - len(args))
            for k in range(n, 0, -1):
                body = body.replace(f'#{k}', args[k - 1])
            out.append(' ' + expand_simple(body) + ' ')
        elif name in verse:
            args, i = _args(tex, m.end(), verse[name])
            out.append(' ' + '। '.join(expand_simple(a) for a in args) + '॥ ')
        else:
            out.append(tex[m.start():m.end()]); i = m.end()
    return expand_simple(''.join(out))


def expand_simple(s):
    s = re.sub(r'\\footnote\{[^{}]*\}', '', s)
    s = re.sub(r'\{\\scriptsize[^{}]*\}', '', s)
    s = re.sub(r'\\devanumber\{(\\arabic\{\w+\}|[^{}]*)\}', '', s)
    s = re.sub(r'\\(refstepcounter|newcounter|setcounter|resetShloka|value|arabic)\{[^{}]*\}(\{[^{}]*\})?', '', s)
    s = s.replace('\\lbrack', '[').replace('\\rbrack', ']').replace('\\-', '').replace('\\\\', ' ')
    s = re.sub(r'\\(textbf|centerline|underline|mbox)\{', '{', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?', ' ', s)
    s = s.replace('{', ' ').replace('}', ' ')
    s = re.sub(r'\((ऋक्|[A-Z][A-Z ]*)\)', ' ', s)
    return s


def sections(src=None):
    src = src or fetch.fetch_all()
    tex = src['vmb_mahanyasa'].read_text(encoding='utf-8')
    parts = re.split(r'\\sect\{([^}]*)\}', tex)
    out = []
    for k in range(1, len(parts), 2):
        title, body = parts[k], parts[k + 1]
        out.append((title, expand(body)))
        if title == LAST_SECTION:
            break
    return out


def units(src=None):
    out = []
    for n, (title, text) in enumerate(sections(src), 1):
        itr = dev_to_itrans(text.replace('[', ' ').replace(']', ' '))
        itr = re.sub(r'\s+', ' ', itr).strip()
        out.append({'id': f'mahanyasa-{n:02d}', 'title': title, 'kind': 'svara',
                    'phrases': svara_phrases(itr)})
    return out


if __name__ == '__main__':
    for u in units():
        n = sum(len(syllabify(p)[0]) for p, _ in u['phrases'])
        print(f"{u['id']} {u['title']}: {len(u['phrases'])} phrases, {n} syllables")
