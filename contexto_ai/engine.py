"""Geração de candidatos usando vetores do spaCy e ranques do Contexto."""
from __future__ import annotations
import math
from pathlib import Path
from functools import lru_cache
import numpy as np

START_WORDS = [
    "pessoa", "objeto", "lugar", "natureza", "animal", "comida", "tempo",
    "trabalho", "dinheiro", "arte", "ciência", "sentimento", "esporte"
]


def same_word_family(a: str, b: str, lemma_a: str = "", lemma_b: str = "") -> bool:
    """Evita palpites que o Contexto pode tratar como a mesma palavra.

    O spaCy reconhece lemas de muitas flexões; o teste de sufixos é uma
    proteção extra para formas ambíguas fora de uma frase (poder/poderem).
    Conservador: NÃO trata palavras apenas parecidas como equivalentes.
    """
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return True
    if lemma_a and lemma_b and lemma_a == lemma_b:
        return True

    shorter, longer = sorted((a, b), key=len)
    if len(shorter) < 4 or not longer.startswith(shorter):
        return False
    suffix = longer[len(shorter):]
    return suffix in {
        "s", "es", "em", "mos", "am", "ão", "ei", "ou", "ava", "avam",
        "emos", "eis", "íamos", "iam", "ando", "endo", "indo",
    }


def unit_vector(vec):
    v = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(v))
    return v / norm if norm > 1e-8 else np.zeros_like(v)


def fit_calibration(samples: list[tuple[float, int, int]]):
    """Aprende log(rank) ≈ intercepto + inclinação * similaridade.

    Só ativa com pelo menos 3 partidas resolvidas e 25 exemplos utilizáveis.
    É um ajuste estatístico inicial, não uma rede neural treinada do zero.
    """
    if len(samples) < 25 or len({x[2] for x in samples}) < 3:
        return None
    similarities = np.asarray([x[0] for x in samples], dtype=np.float64)
    ranks = np.asarray([x[1] for x in samples], dtype=np.float64)
    y = np.log1p(ranks)
    x = similarities
    # Regressão linear com regularização fraca para evitar instabilidade.
    xc = x - x.mean()
    yc = y - y.mean()
    slope = float(np.dot(xc, yc) / (np.dot(xc, xc) + 0.03))
    if not np.isfinite(slope) or slope >= -0.2:
        return None
    intercept = float(y.mean() - slope * x.mean())
    return intercept, slope


def score_matrix(matrix: np.ndarray, guess_vectors: np.ndarray, ranks: list[int],
                 calibration=None) -> np.ndarray:
    """Pontua cada possível resposta de acordo com os palpites já classificados."""
    if len(ranks) == 0:
        return np.zeros(len(matrix), dtype=np.float32)
    sims = matrix @ guess_vectors.T
    ordered = sorted(range(len(ranks)), key=lambda i: ranks[i])
    best = ordered[0]
    close = ordered[:min(5, len(ordered))]
    weights = np.array([1.0 / (max(ranks[i], 1) ** 0.85) for i in close], dtype=np.float32)
    weights /= weights.sum()
    # O melhor palpite é a âncora principal. Os outros ajudam a orientar.
    affinity = 0.70 * sims[:, best] + 0.30 * (sims[:, close] @ weights)

    # Respeita a ordem: um palpite com rank 16 deve ser semanticamente
    # mais parecido com a solução hipotética que um com rank 2182.
    consistency = np.zeros(len(matrix), dtype=np.float32)
    pairs = 0
    top = ordered[:min(8, len(ordered))]
    for a_idx, i in enumerate(top):
        for j in top[a_idx + 1:]:
            if ranks[i] == ranks[j]:
                continue
            gap = np.log1p(ranks[j]) - np.log1p(ranks[i])
            consistency += np.tanh(5 * (sims[:, i] - sims[:, j])) * min(gap / 3, 1.0)
            pairs += 1
    if pairs:
        consistency /= pairs
    score = affinity + 0.12 * consistency

    # Após várias partidas concluídas, passa a usar a relação real observada
    # entre similaridade dos vetores e rankings (aprendizado simples).
    if calibration is not None:
        intercept, slope = calibration
        predicted = intercept + slope * sims
        actual = np.log1p(np.asarray(ranks, dtype=np.float32))
        # Melhores rankings são mais informativos.
        relevance = 1.0 / np.sqrt(np.asarray(ranks, dtype=np.float32) + 5)
        relevance /= relevance.sum()
        error = np.minimum(np.abs(predicted - actual), 10)
        score = score - 0.045 * (error @ relevance)
    return score


class SuggestionEngine:
    def __init__(self, cache_dir: str | Path, vocabulary_size: int = 18000):
        try:
            import spacy
            from wordfreq import top_n_list
        except ImportError as exc:
            raise RuntimeError("Dependências não instaladas. Leia o README.") from exc

        try:
            # Mantém o lematizador: o Contexto muitas vezes agrupa
            # conjugações/plurais (poder, poderes, poderem...).
            # Não precisamos do parser de frases nem de entidades nomeadas.
            self.nlp = spacy.load("pt_core_news_md", exclude=["parser", "ner"])
        except OSError as exc:
            raise RuntimeError(
                "Modelo português ausente. Execute: python -m spacy download pt_core_news_md"
            ) from exc

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        version = self.nlp.meta.get('version', 'unknown')
        cache_file = self.cache_dir / f"vocab_{vocabulary_size}_pt_{version}.npz"
        if cache_file.exists():
            data = np.load(cache_file, allow_pickle=False)
            self.words = data['words'].tolist()
            self.matrix = data['matrix'].astype(np.float32)
        else:
            print("Preparando o dicionário em português (só na primeira vez)...")
            raw = top_n_list("pt", vocabulary_size)
            words, vectors = [], []
            for word in dict.fromkeys(raw + START_WORDS):
                word = word.strip().lower()
                if not word.isalpha() or len(word) < 3 or len(word) > 23:
                    continue
                # Sem artigos, preposições e conectivos comuns nas sugestões.
                if word in self.nlp.Defaults.stop_words and word not in START_WORDS:
                    continue
                if not self.nlp.vocab.has_vector(word):
                    continue
                vec = unit_vector(self.nlp.vocab.get_vector(word))
                if np.any(vec):
                    words.append(word)
                    vectors.append(vec)
            if not vectors:
                raise RuntimeError("O modelo português não possui vetores carregados.")
            self.words = words
            self.matrix = np.stack(vectors).astype(np.float32)
            np.savez_compressed(cache_file, words=np.asarray(words), matrix=self.matrix)
        self.indices = {word: i for i, word in enumerate(self.words)}

    @lru_cache(maxsize=4096)
    def lemma(self, word: str) -> str:
        """Devolve a forma de dicionário aproximada (calculada sob demanda)."""
        word = word.strip().lower()
        doc = self.nlp(word)
        if not doc:
            return word
        lemma = doc[0].lemma_.strip().lower()
        return lemma or word

    def vector(self, word: str):
        word = word.lower().strip()
        if word in self.indices:
            return self.matrix[self.indices[word]]
        if not self.nlp.vocab.has_vector(word):
            return None
        result = unit_vector(self.nlp.vocab.get_vector(word))
        return result if np.any(result) else None

    def calibration(self, historical_examples):
        records = []
        for answer, guess, rank, game_id in historical_examples:
            a, g = self.vector(answer), self.vector(guess)
            if a is None or g is None:
                continue
            records.append((float(np.dot(a, g)), rank, game_id))
        return fit_calibration(records)

    def suggest(self, guesses: list[dict], historical_examples=None, n: int = 5):
        historical_examples = historical_examples or []
        tried = {g['word'].lower().strip() for g in guesses}
        # Além da palavra exata, bloqueia flexões já tentadas.
        tried_lemmas = {word: self.lemma(word) for word in tried}
        def already_used_variant(word: str) -> bool:
            candidate_lemma = self.lemma(word)
            return any(same_word_family(word, attempted, candidate_lemma, attempted_lemma)
                       for attempted, attempted_lemma in tried_lemmas.items())

        valid = [(v, int(g['rank'])) for g in guesses
                 if (v := self.vector(g['word'])) is not None]
        if not valid:
            result = [w for w in START_WORDS if not already_used_variant(w)]
            return result[:n]
        guess_vectors = np.stack([v for v, _ in valid])
        ranks = [r for _, r in valid]
        scores = score_matrix(self.matrix, guess_vectors, ranks,
                              self.calibration(historical_examples))
        order = np.argsort(-scores)
        result = []
        result_lemmas = {}
        for idx in order:
            word = self.words[int(idx)]
            if word in tried or already_used_variant(word):
                continue
            candidate_lemma = self.lemma(word)
            # Evita sugerir flexões da mesma palavra na mesma lista.
            if any(same_word_family(word, earlier, candidate_lemma, earlier_lemma)
                   for earlier, earlier_lemma in result_lemmas.items()):
                continue
            # Evita sugerir 5 variantes quase idênticas em sequência.
            vec = self.matrix[int(idx)]
            if any(float(np.dot(vec, self.matrix[self.indices[w]])) > 0.97 for w in result):
                continue
            result.append(word)
            result_lemmas[word] = candidate_lemma
            if len(result) >= n:
                break
        return result
