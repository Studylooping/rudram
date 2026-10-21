"""Download the source texts (not redistributed in this repo; see README) and pin them by sha256.

  python -m rudram.fetch
"""
import hashlib
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
_VMB = 'https://raw.githubusercontent.com/stotrasamhita/vedamantra-book/3bbc26b6b2af50f00b29e7e4c3f3b539f3254c7d/'
_KYV = 'https://raw.githubusercontent.com/KYVeda/texts/76fe735ac1344faa73dbe4dac57a1311d54c1dfb/'
SOURCES = {
    # recited text (primary): svara-marked ITRANS, Rajagopal Iyer & Rekha Venkatesh
    'sd_rudra': ('https://sanskritdocuments.org/doc_veda/rudra.itx', 'rudra.itx',
                 'd8c1f9fb88119943d4c13c70ef0dcef59c5a369e77dcb32728a26cbee4173ec6'),  # "August 29, 2024"
    'sd_chamaka': ('https://sanskritdocuments.org/doc_veda/chamaka.itx', 'chamaka.itx',
                   'b5c3a9bbdc3514886a457eae20358759532097630b1710a00540f6fcaeea1290'),  # "March 19, 2022"
    # Mahanyasa + cross-check copy of Rudra/Chamaka: stotrasamhita/vedamantra-book (Unicode, svara)
    'vmb_mahanyasa': (_VMB + 'mantras/MahaNyasah.tex', 'vmb/MahaNyasah.tex',
                      'bfeafb8338d845419c6e48d6fd034388ed25eaa07597dd6dae57f39443e5dfc4'),
    'vmb_rudra': (_VMB + 'mantras/RudraPrashnah.tex', 'vmb/RudraPrashnah.tex',
                  '00beb2bbcf5021345789f2b0464f2e9823dec4f3f383905c8c53a88b5808418c'),
    'vmb_chamaka': (_VMB + 'mantras/ChamakaPrashnah.tex', 'vmb/ChamakaPrashnah.tex',
                    '1a74f8e10785ebd92d8cebd33b9d283e3d0d12f600ad290188d0f3bd1ab12919'),
    # independent saMhitA text (TS kANDa 4, Baraha ASCII with svaras), KYVeda/texts
    'kyveda_ts4': (_KYV + 'saMhitA/04/TS%204%20Baraha.BRH', 'kyveda/TS4_Baraha.BRH',
                   '48d40cea6bc631cd22add2d447fdf0ad29151309063012eabb98b61eda0095ea'),
}


def _get(url, dest, sha, force=False):
    if dest.exists() and not force:
        data = dest.read_bytes()
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        # sanskritdocuments.org answers 406 to Python's default User-Agent
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (rudram-fetch)'})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        dest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha:
        raise RuntimeError(f'{dest.name}: sha256 {digest} differs from the pinned, verified revision {sha}')
    return dest


def fetch_all(force=False):
    return {k: _get(url, DATA / name, sha, force) for k, (url, name, sha) in SOURCES.items()}


def _between(text, start, end):
    i = text.index(start)
    return text[i + len(start): text.index(end, i)]


# Svara corrections to the primary text, each made only where BOTH independent references
# (vedamantra-book and KYVeda TS 4) agree against it; found by rudram.crosscheck (see TEXT.md).
CORRECTIONS = [
    ('chamaka', "varma\\' cha me\\`.a~NgA\\'ni", "varma\\' cha\\` me.a~NgA\\'ni",
     'TS 4.7.1 (camaka anuvaka 1): ca anudAtta, me unmarked (vmb वर्म॑ च॒ मेऽङ्गा॑नि; KYVeda varma# caq mE &~ggA#ni)'),
    ('chamaka', "vi\\`ttaM cha me\\`", "vi\\`ttaM cha\\' me\\`",
     'TS 4.7.5 (camaka anuvaka 5): ca svarita (vmb वि॒त्तं च॑ मे॒; KYVeda viqttaM ca# mEq)'),
]


def section_itrans(src=None):
    """Svara-ITRANS text of the recited parts, from the primary (sanskritdocuments) files."""
    src = src or fetch_all()
    r = src['sd_rudra'].read_text(encoding='utf-8')
    c = src['sd_chamaka'].read_text(encoding='utf-8')
    namaka = _between(r, '\\section{|| shrI rudraprashnaH (namakam) ||}', '##\nSee chamakam')
    chamaka = c[c.index('\\begin{document}'):]
    chamaka = chamaka[chamaka.index('\\endtitles ##') + len('\\endtitles ##'): chamaka.index('##\nSee namakam')]
    strip = lambda t: re.sub(r'\(\.\..*?\.\.\)', ' ', t, flags=re.S)  # colophons "(.. iti ... ..)"
    out = {'namaka': strip(namaka), 'chamaka': strip(chamaka)}
    for part, a, b, _ in CORRECTIONS:
        if out[part].count(a) != 1:
            raise RuntimeError(f'correction target not found exactly once in {part}: {a!r}')
        out[part] = out[part].replace(a, b)
    out['rudra_file'] = r
    return out


if __name__ == '__main__':
    for k, p in fetch_all().items():
        print(k, p)
