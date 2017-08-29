from __future__ import print_function

import codecs
from collections import Counter
from collections import OrderedDict

ID, FORM, LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC = range(10)

EMPTY = 0
MULTIWORD = 1

def isempty(token):
    if isinstance(token, list):
        token = token[ID]
    return token[2] == EMPTY if isinstance(token, tuple) else False

def ismultiword(token):
    if isinstance(token, list):
        token = token[ID]
    return token[2] == MULTIWORD if isinstance(token, tuple) else False

def read_conllu(filename, skip_empty=True, skip_multiword=True, parse_feats=False, parse_deps=False):

    def _parse_sentence(lines):
        sentence = []
        for line in lines:
            token = _parse_token(line)
            if skip_empty and isempty(token):
                continue
            if skip_multiword and ismultiword(token):
                    continue
            sentence.append(token)
        return sentence

    def _parse_token(line):
        fields = line.split("\t")

        if "." in fields[ID]:
            token_id, index = fields[ID].split(".")
            id = (int(token_id), int(index), EMPTY)
        elif "-" in fields[ID]:
            start, end = fields[ID].split("-")
            id = (int(start), int(end), MULTIWORD)
        else:
            id = int(fields[ID])
        fields[ID] = id

        for f in [LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC]:
            if fields[f] == "_":
                fields[f] = None

        if parse_feats and fields[FEATS]:
            fields[FEATS] = _parse_feats(fields[FEATS])

        if fields[HEAD]:
            fields[HEAD] = int(fields[HEAD])

        if parse_deps and fields[DEPS]:
            fields[DEPS] = _parse_deps(fields[DEPS])

        return fields

    def _parse_feats(str):
        feats = OrderedDict()
        for key, value in [feat.split("=") for feat in str.split("|")]:
            if "," in value:
                value = value.split(",")
            feats[key] = value
        return feats

    def _parse_deps(str):
        return list(map(lambda rel: (int(rel[0]), rel[1]), [rel.split(":") for rel in str.split("|")]))

    lines = []
    with codecs.open(filename, "r", "utf-8") as fp:
        for line in fp:
            line = line.rstrip("\r\n")
            if line.startswith("#"):
                continue
            if not line:
                if len(lines) != 0:
                    yield _parse_sentence(lines)
                    lines = []
                continue
            lines.append(line)
        if len(lines) != 0:
            yield _parse_sentence(lines)

def normalize_lower(field, value):
    return value.lower() if field == FORM else value

def create_dictionary(sentences, fields={FORM, LEMMA, UPOS, XPOS, FEATS, DEPREL}, normalize=normalize_lower):
    dic = [None for _ in range(10)]
    for f in fields:
        dic[f] = Counter()

    for sentence in sentences:
        for token in sentence:
            for f in fields:
                s = token[f]
                if normalize:
                    s = normalize(f, s)
                dic[f][s] += 1

    return tuple(dic)

def create_index(dic, min_frequency=1):

    for f, c in enumerate(dic):
        if not c:
            continue
        ordered = c.most_common()
        min_fq = min_frequency[f] if isinstance(min_frequency, list) else min_frequency
        for i, (s, fq) in enumerate(ordered):
            if fq >= min_fq:
                c[s] = i + 1
            else:
                del c[s]

    return dic

def create_inverse_index(index):
    inverse = []
    for c in index:
        inverse.append({v: k for k, v in c.items()} if c is not None else None)
    return tuple(inverse)

def map_to_instance(sentences, index, fields=[FORM, UPOS, FEATS]):
    pass

if __name__ == "__main__":
    dic = create_dictionary(read_conllu("../../test/test1.conllu"), fields={UPOS})
    print(dic)

    index = create_index(dic, min_frequency=3)
    print(index)

    inverse_index = create_inverse_index(index)
    print(inverse_index)
