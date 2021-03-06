from __future__ import print_function

import codecs
import heapq
import numpy as np
import re
import random
from collections import Counter, OrderedDict, namedtuple, defaultdict
from functools import total_ordering

# Priradenie 0-10
ID, FORM, LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC = range(10)

EMPTY = 0
MULTIWORD = 1

FIELD_TO_STR = ["id", "form", "lemma", "upos", "xpos", "feats", "head", "deprel", "deps", "misc"]
# Vytvorenie dvojic premenna:id premennej
STR_TO_FIELD = {k : v for v, k in enumerate(FIELD_TO_STR)}

''' Vrati, ci je token prazdny '''
def isempty(token):
    # Ak je 'token' typu 'list'
    if isinstance(token, list):
        token = token[ID]
    # Ak je 'token' typu 'tuple', vrat ci je 'token[2]' == 0 (pozn. inicializovane EMPTY = 0), inak false
    return token[2] == EMPTY if isinstance(token, tuple) else False

''' Vrati, ci je token viacslovny '''
def ismultiword(token):
    if isinstance(token, list):
        token = token[ID]
    # Ak je 'token' typu 'tuple', vrat ci je 'token[2]' == 1 (pozn. inicializovane MULTIWORD = 1), inak false
    return token[2] == MULTIWORD if isinstance(token, tuple) else False
    
''' Zmeni velke pismena na male vo 'FORM' '''
def normalize_lower(field, value):
    # Ak je 'value' FORM, t.j. slovo, vo 'value' zmeni velke pismena na male
    return value.lower() if field == FORM else value

_NUM_REGEX = re.compile("[0-9]+|[0-9]+\\.[0-9]+|[0-9]+[0-9,]+")
NUM_FORM = u"__number__"

''' Ak je field FORM, zmeni velke pismena na male,
    ak je field cislo, vrati, ze je to cislo,
    inak vrati povodnu hodnotu value.
'''
def normalize_default(field, value):
    # Ak 'value' nie je 'FORM', t.j. slovo
    if field != FORM:
        return value
    # Porovnanie s 'value' ci obsahuje znaky/symboly/cisla
    if _NUM_REGEX.match(value):
        return NUM_FORM
    # Zmeni velke pismena na male
    value = value.lower()
    return value

def read_conllu(filename, skip_empty=True, skip_multiword=True, parse_feats=False, parse_deps=False, normalize=normalize_default):

    ''' Vrati pole tokenov bez bielych znakov, odstrani viacslovne tokeny '''
    def _parse_sentence(lines):
        sentence = []
        for line in lines:
            token = _parse_token(line)
            # Preskoci prazdny token
            if skip_empty and isempty(token):
                continue
            # Preskoci viacslovne slovo
            if skip_multiword and ismultiword(token):
                continue
            sentence.append(token)
        return sentence

    ''' Vrati  sparsovany line:
        - skontroluje ID a zmeni ho na integer,
        - zmeni znak '_' na 'None', 
        - rozparsuje jednotlive FEATS,
        - rodica zmeni na integer, 
        - DEPS
        - znormalizuje FORM a LEMMA (lowcase, ...).
    '''
    def _parse_token(line):
        fields = line.split("\t")

        # Ak je v 'ID' bodka
        if "." in fields[ID]:
            # Vytvori trojicu (cast pred bodkou, cast za bodkou, 0), pozn. inicializovane EMPTY = 0 
            token_id, index = fields[ID].split(".")
            id = (int(token_id), int(index), EMPTY)
        # Ak je v 'ID' pomlcka
        elif "-" in fields[ID]:
            # Vytvori trojicu (cast pred pomlckou, cast za pomlckou, 1), pozn. inicializovane MULTIWORD = 1 
            start, end = fields[ID].split("-")
            id = (int(start), int(end), MULTIWORD)
        else:
            # V ostatnych pripadoch ponecha povodne ID
            id = int(fields[ID])
        fields[ID] = id

        # V kazdom ... nahradi znak "_" symbolom 'None'
        for f in [LEMMA, UPOS, XPOS, FEATS, HEAD, DEPREL, DEPS, MISC]:
            if fields[f] == "_":
                fields[f] = None

        # Ak True, zmeni FEATS v fields na OrderedDict(kluc, hodnota) vlastnosti FEATS        
        if parse_feats and fields[FEATS]:
            fields[FEATS] = _parse_feats(fields[FEATS])

        # AK existuje predok tokenu, zmeni jeho typ zo string na integer
        if fields[HEAD]:
            fields[HEAD] = int(fields[HEAD])

        # Ak existuje DEPS, vlozi sparsovane DEPS do fields[DEPS]
        if parse_deps and fields[DEPS]:
            fields[DEPS] = _parse_deps(fields[DEPS])

        # Znormalizuje podla def normalize_default FORM a LEMMA v 'line'
        if normalize:
            for f in [FORM, LEMMA]:
                fields[f] = normalize(f, fields[f])
        
        return fields

    ''' Z retazca vyberie jednotlive vlastnosti, ktore ulozi do OrderedDict (kluc, hodnota)'''
    def _parse_feats(str):
        feats = OrderedDict()
        for key, value in [feat.split("=") for feat in str.split("|")]:
            if "," in value:
                value = value.split(",")
            feats[key] = value
        return feats

    ''' Vrati list vlastnosti deps zo stringu oddelenych znakmi ":" a "|" '''
    def _parse_deps(str):
        return list(map(lambda rel: (int(rel[0]), rel[1]), [rel.split(":") for rel in str.split("|")]))

    lines = []
    # Citanie zo suboru
    with codecs.open(filename, "r", "utf-8") as fp:
        for line in fp:
            # Oddeli riadky
            line = line.rstrip("\r\n")
            # Preskoci komentare 
            if line.startswith("#"):
                continue
            if not line:
                # Ak nie je riadok, ale dlzka vsetkych riadkov !=0, sparsuje lines pomocou funkcie _parse_sentence
                if len(lines) != 0:
                    yield _parse_sentence(lines)
                    lines = []
                continue
            # Prida do pola riadkov bez komentarov, ...
            lines.append(line)
        if len(lines) != 0:
            yield _parse_sentence(lines)

''' Vrati dvojicu field:Counter, kde pre vsetky sentences spocita, kolko sa v nich jednotlivych fields '''
def create_dictionary(sentences, fields={FORM, LEMMA, UPOS, XPOS, FEATS, DEPREL}):
    dic = {f: Counter() for f in fields}
    for sentence in sentences:
        for token in sentence:
            for f in fields:
                s = token[f]
                dic[f][s] += 1
    return dic

''' Vrati dvojicu field:Counter, kde zmeni frekvenciu vyskytov fieldov na minimalnu frekvenciu = 1 '''
def create_index(dic, min_frequency=1):
    for f, c in dic.items():
        # Zoradi 'c' (Counter) podla poctu vyskytov (od najcastejsie sa vyskytujuce po menej)
        ordered = c.most_common()
        min_fq = min_frequency[f] if isinstance(min_frequency, (list, tuple, dict)) else min_frequency
        for i, (s, fq) in enumerate(ordered):
            if fq >= min_fq:
                c[s] = i + 1
            else:
                del c[s]
    return dic

''' Vrati dvojicu field:dic, kde dic je dvojica pocetVyskytov:slovoTokena '''
def create_inverse_index(index):
    return {f: {v: k for k, v in c.items()} for f, c in index.items()}

INDEX_FILENAME = "{0}_{1}_index.txt"

_NONE_TOKEN = u"__none__"

''' Pre kazdy token, ktory = None, prepise hodnotu na _NONE_TOKEN, vsetky tokeny zapise do suboru '''
def write_index(basename, index, fields={FORM, UPOS, FEATS, DEPREL}):
    index = create_inverse_index(index)
    for f in fields:
        c = index[f]
        # Otvori subory pre zapis
        with codecs.open(INDEX_FILENAME.format(basename, FIELD_TO_STR[f]), "w", "utf-8") as fp:
            for i in range(1, len(c) + 1):
                token = c[i]
                if token is None:
                    token = _NONE_TOKEN
                print(token, file=fp)

''' Vrati dvojicu field:Counter(token), kde:
    - zo suboru cita riadky, 
    - odstrani prazdne znaky sprava,
    - ak sa v token nachadza _NONE_TOKEN, zmeni ho na None,
    - zmeni hodnotu Counter na poradove cislo riadka, v ktorom sa token nachadzal v subore
'''
def read_index(basename, fields={FORM, UPOS, FEATS, DEPREL}):
    index = {}
    # Vytvori Counter pre fields
    for f in fields:
        index[f] = Counter()
        # Otvori subory na citanie
        with codecs.open(INDEX_FILENAME.format(basename, FIELD_TO_STR[f]), "r", "utf-8") as fp:
            i = 1
            for line in fp:
                # Odstrani prazdne znaky sprava
                token = line.rstrip("\r\n")
                if token == _NONE_TOKEN:
                    token = None
                index[f][token] = i
                i += 1
    return index

class DepTree(namedtuple("DepTree", "feats, heads, labels")):

    def __new__(cls, num_tokens, num_feats=0):
        return super(cls, DepTree).__new__(cls,
                np.empty((num_tokens, num_feats), dtype=np.int) if num_feats > 0 else None,
                np.full(num_tokens, -1, dtype=np.int),
                np.full(num_tokens, -1, dtype=np.int))

    ''' Vrati dlzku svojho predka '''
    def __len__(self):
        return len(self.heads)

''' Vrati strom vytvoreny zo 'sentence' '''
def map_to_instance(sentence, index, fields=(FORM, UPOS, FEATS)):
    num_tokens = len(sentence) # dlzka vety
    num_feats = len(fields) # dlzka poli
    tree = DepTree(num_tokens, num_feats)

    # Stromu nastavi feats, heads, labels podla sentence
    for i, token in enumerate(sentence):
        for j, f in enumerate(fields):
            tree.feats[i][j] = index[f][token[f]]
        tree.heads[i] = token[HEAD]
        tree.labels[i] = index[DEPREL][token[DEPREL]]

    return tree

''' Pre kazdu 'sentence' vrati strom '''
def map_to_instances(sentences, index, fields=(FORM, UPOS, FEATS)):
    for sentence in sentences:
        yield map_to_instance(sentence, index, fields)

''' Vrati nahodne data z 'data' '''
def shuffled_stream(data):
    while True:
        random.shuffle(data)
        for d in data:
            yield d

def parse_nonprojective(scores, heads=None):

    def _push(queue, elm):
        heapq.heappush(queue, elm)
    
    def _pop(queue):
        if len(queue) == 0:
            return None
        return heapq.heappop(queue)

    def _find_disjoint_sets(trees, elm):
        if trees[elm] != elm:
            trees[elm] = _find_disjoint_sets(trees, trees[elm])
        return trees[elm]

    def _union_disjoint_sets(trees, set1, set2):
        trees[set2] = set1

    def _invert_max_branching(node, h, visited, inverted):
        visited[node] = True
        for v in h[node]:
            if visited[v]:
                continue
            inverted[v - 1] = node
            _invert_max_branching(v, h, visited, inverted)

    nr, nc = scores.shape

    roots = list(range(1, nr))
    rset = [0]

    q = np.empty(nr, dtype=np.object)
    enter = np.empty(nr, dtype=np.object)

    min = np.arange(nr, dtype=np.int)
    s = np.arange(nr, dtype=np.int)
    w = np.arange(nr, dtype=np.int)

    h = defaultdict(list)

    for node in range(1, nr):
        q[node] = []
        for i in range(nr):
            if i != node:
                _push(q[node], _Edge(i, node, scores[i, node]))

    while roots:
        scc_to = roots.pop()
        max_in_edge = _pop(q[scc_to])

        if max_in_edge is None:
            rset.append(scc_to)
            continue

        scc_from = _find_disjoint_sets(s, max_in_edge.start)
        if scc_from == scc_to:
            roots.append(scc_to)
            continue

        h[max_in_edge.start].append(max_in_edge.end)

        wss_from = _find_disjoint_sets(w, max_in_edge.start)
        wss_to = _find_disjoint_sets(w, max_in_edge.end)
        if wss_from != wss_to:
            _union_disjoint_sets(w, wss_from, wss_to)
            enter[scc_to] = max_in_edge
            continue

        min_weight = np.inf
        min_scc = -1
        tmp = max_in_edge
        while tmp is not None:
            if tmp.weight < min_weight:
                min_weight = tmp.weight
                min_scc = _find_disjoint_sets(s, tmp.end)
            tmp = enter[_find_disjoint_sets(s, tmp.start)]

        inc = min_weight - max_in_edge.weight
        for e in q[scc_to]:
            e.weight += inc

        min[scc_to] = min[min_scc]

        tmp = enter[scc_from]
        while tmp is not None:
            inc = min_weight - tmp.weight
            tmp_scc_to = _find_disjoint_sets(s, tmp.end)
            for e in q[tmp_scc_to]:
                e.weight += inc
                _push(q[scc_to], e)

            _union_disjoint_sets(s, scc_to, tmp_scc_to)
            q[tmp_scc_to] = None
            tmp = enter[_find_disjoint_sets(s, tmp.start)]

        roots.append(scc_to)

    visited = np.zeros(nr, dtype=np.bool)
    if heads is None:
        heads = -np.ones(nr - 1, dtype=np.int)
    for scc in rset:
        _invert_max_branching(min[scc], h, visited, heads)

    return heads

@total_ordering
class _Edge(object):

    def __init__(self, start, end, weight):
        self.start = start
        self.end = end
        self.weight = weight

    def __eq__(self, other):
        return (self.weight, self.start, self.end) == (other.weight, other.start, other.end)

    def __lt__(self, other):
        return (-self.weight, self.start, self.end) < (-other.weight, other.start, other.end)

    def __repr__(self):
        return str((self.start, self.end, self.weight))

def parse_projective(scores):
    nr, nc = scores.shape
    N = nr - 1

    complete_0 = np.zeros((nr, nr)) # s, t, direction (right=1).
    complete_1 = np.zeros((nr, nr)) # s, t, direction (right=1).
    incomplete_0 = np.zeros((nr, nr)) # s, t, direction (right=1).
    incomplete_1 = np.zeros((nr, nr)) # s, t, direction (right=1).

    complete_backtrack = -np.ones((nr, nr, 2), dtype=np.int) # s, t, direction (right=1).
    incomplete_backtrack = -np.ones((nr, nr, 2), dtype=np.int) # s, t, direction (right=1).

    for i in range(nr):
        incomplete_0[i, 0] = -np.inf

    for k in range(1, nr):
        for s in range(nr - k):
            t = s + k
            tmp = -np.inf
            maxidx = s
            for r in range(s, t):
                cand = complete_1[s, r] + complete_0[r+1, t]
                if cand > tmp:
                    tmp = cand
                    maxidx = r
                if s == 0 and r == 0:
                    break
            incomplete_0[t, s] = tmp + scores[t, s]
            incomplete_1[s, t] = tmp + scores[s, t]
            incomplete_backtrack[s, t, 0] = maxidx
            incomplete_backtrack[s, t, 1] = maxidx

            tmp = -np.inf
            maxidx = s
            for r in range(s, t):
                cand = complete_0[s, r] + incomplete_0[t, r]
                if cand > tmp:
                    tmp = cand
                    maxidx = r
            complete_0[s, t] = tmp
            complete_backtrack[s, t, 0] = maxidx

            tmp = -np.inf
            maxidx = s + 1
            for r in range(s+1, t+1):
                cand = incomplete_1[s, r] + complete_1[r, t]
                if cand > tmp:
                    tmp = cand
                    maxidx = r
            complete_1[s, t] = tmp
            complete_backtrack[s, t, 1] = maxidx

    heads = -np.ones(N, dtype=np.int)
    _backtrack_eisner(incomplete_backtrack, complete_backtrack, 0, N, 1, 1, heads)
    return heads

def _backtrack_eisner(incomplete_backtrack, complete_backtrack, s, t, direction, complete, heads):
    if s == t:
        return
    if complete:
        r = complete_backtrack[s, t, direction]
        if direction:
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, s, r, 1, 0, heads)
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, r, t, 1, 1, heads)
            return
        else:
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, s, r, 0, 1, heads)
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, r, t, 0, 0, heads)
            return
    else:
        r = incomplete_backtrack[s, t, direction]
        if direction:
            heads[t-1] = s
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, s, r, 1, 1, heads)
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, r + 1, t, 0, 1, heads)
            return
        else:
            heads[s-1] = t
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, s, r, 1, 1, heads)
            _backtrack_eisner(incomplete_backtrack, complete_backtrack, r + 1, t, 0, 1, heads)
            return

def is_projective(heads):
    n_len = heads.shape[0]
    for i in range(n_len):
        if heads[i] < 0:
            continue
        for j in range(i + 1, n_len):
            if heads[j] < 0:
                continue
            edge1_0 = min(i, heads[i])
            edge1_1 = max(i, heads[i])
            edge2_0 = min(j, heads[j])
            edge2_1 = max(j, heads[j])
            if edge1_0 == edge2_0:
                if edge1_1 == edge2_1:
                    return False
                else:
                    continue
            if edge1_0 < edge2_0 and not (edge2_0 >= edge1_1 or edge2_1 <= edge1_1):
                return False
            if edge1_0 > edge2_0 and not (edge1_0 >= edge2_1 or edge1_1 <= edge2_1):
                return False
    return True
