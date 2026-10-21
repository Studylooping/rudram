from rudram.crosscheck import baraha_to_itrans, dev_to_itrans
from rudram.itrans import devanagari, syllabify


def svaras(itrans):
    return ''.join(s.svara for s in syllabify(itrans)[0])


def test_namaka_opening():
    syls, notes = syllabify(r"nama\'ste rudra ma\`nyava\' u\`tota\` iSha\'ve\` nama\'H")
    assert devanagari(syls, marks=True) == 'नम॑स्ते रुद्र म॒न्यव॑ उ॒तोत॒ इष॑वे॒ नमः॑'
    assert [s.matra for s in syls] == [1, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]
    assert not notes


def test_post_counts_consonants_and_coda():
    syls, _ = syllabify(r"rudra ma\`nyava\'")
    # ru|dra: 'u' is followed by d r; final a by m (next word); ma-nya: 'a' followed by n y
    assert [s.post for s in syls] == [2, 1, 2, 1, 0]


def test_mark_after_coda_consonant_belongs_to_vowel():
    assert svaras(r"ahIg\'shcha\`") == 'USA'
    assert svaras(r"va\`r__\`Sham") == 'AU'  # mark on a svarabhakti r is not a syllable svara


def test_gum_anusvara_and_pluta():
    syls, _ = syllabify(r"hi{\m+}\'sI\`H o3m")
    assert syls[0].coda == ['gm'] and syls[0].svara == 'S'
    assert syls[-1].matra == 3


def test_avagraha_is_no_syllable():
    assert len(syllabify(r"ta\`nUragho\`rA.apA\'pakAshinI")[0]) == 10


def test_sources_convert_to_same_syllables():
    ours = r"nama\'ste rudra ma\`nyava\' u\`tota\` iSha\'ve\` nama\'H"
    dev = dev_to_itrans('नम॑स्ते रुद्र म॒न्यव॑ उ॒तो त॒ इष॑वे॒ नमः॑')
    brh = baraha_to_itrans('nama#stE rudra maqnyava# uqtOtaq iSha#vEq nama#H')
    assert svaras(ours) == svaras(dev) == svaras(brh)


def test_word_final_consonant_stays_with_its_word():
    syls, _ = syllabify(r"a\`smAnvR^i\'Naktu vi\`shvata\'H")
    assert devanagari(syls) == 'अस्मान्वृणक्तु विश्वतः'
    syls, _ = syllabify(r"a\`smAn vR^i\'Naktu")
    assert devanagari(syls) == 'अस्मान् वृणक्तु'
    assert [s.post for s in syls] == [2, 2, 1, 2, 0]  # timing unchanged: n v still follow mA
