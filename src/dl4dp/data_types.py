from __future__ import print_function

import numpy as np
from collections import namedtuple

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

class DepTree(namedtuple("DepTree", "feats, heads, labels")):

    def __new__(cls, shape):
        return super(cls, DepTree).__new__(cls,
                np.empty(shape, dtype=np.int),
                np.full(shape[0], -1, dtype=np.int),
                np.full(shape[0], -1, dtype=np.int))

def map_to_instance(sentence, index, fields=[FORM, UPOS, FEATS]):
    l = len(sentence)
    f_num = len(fields)
    tree = DepTree((l, f_num))

    for i, token in enumerate(sentence):
        for j, f in enumerate(fields):
            tree.feats[i][j] = index[f][token[f]]
        tree.heads[i] = token[HEAD]
        tree.labels[i] = index[DEPREL][token[DEPREL]]

    return tree

def map_to_instances(sentences, index, fields=[FORM, UPOS, FEATS]):
    for sentence in sentences:
        yield map_to_instance(sentence, index, fields)