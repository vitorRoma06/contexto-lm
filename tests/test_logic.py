import sqlite3
import numpy as np
from contexto_ai.database import Store
from contexto_ai.engine import fit_calibration, score_matrix, unit_vector


def test_store_saves_guesses_and_solution(tmp_path):
    store = Store(tmp_path / 'test.sqlite3')
    game = store.new_game()
    assert store.active_game() == game
    store.add_guess(game, 'poder', 16)
    assert store.guesses(game) == [{'word':'poder','rank':16}]
    store.finish(game, 'capacidade')
    assert store.active_game() is None
    assert store.guesses(game)[-1] == {'word':'capacidade','rank':1}
    assert len(store.previous_examples()) == 2
    assert store.stats()[0]['answer'] == 'capacidade'
    store.close()


def test_closest_to_best_guess_scores_higher():
    matrix = np.stack([unit_vector([1., 0., 0.]), unit_vector([0.,1.,0.])])
    vecs = np.stack([unit_vector([1., 0., 0.])])
    scores = score_matrix(matrix, vecs, [16])
    assert scores[0] > scores[1]


def test_calibration_requires_multiple_games():
    assert fit_calibration([(0.9,1,1), (0.1,1000,1)]*20) is None
    samples = []
    for g in (1,2,3):
        for i in range(10):
            sims = 1.0-i*0.09
            rank = 1 + int(1500 * (1-sims))
            samples.append((sims,rank,g))
    calibration = fit_calibration(samples)
    assert calibration is not None
    assert calibration[1] < 0
