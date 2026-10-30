"""Histórico local de partidas; nenhuma informação é enviada para um servidor."""
from __future__ import annotations
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, file: str | Path):
        self.file = Path(file)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.file)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                answer TEXT
            );
            CREATE TABLE IF NOT EXISTS guesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                word TEXT NOT NULL,
                rank INTEGER NOT NULL CHECK (rank >= 1),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, word)
            );
        """)
        self.db.commit()

    def new_game(self) -> int:
        cur = self.db.execute("INSERT INTO games DEFAULT VALUES")
        self.db.commit()
        return int(cur.lastrowid)

    def active_game(self) -> int | None:
        row = self.db.execute(
            "SELECT id FROM games WHERE finished_at IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return int(row['id']) if row else None

    def add_guess(self, game_id: int, word: str, rank: int):
        word = word.strip().lower()
        if not word or rank < 1:
            raise ValueError("Palavra ou ranking inválido")
        existing = self.db.execute(
            "SELECT rank FROM guesses WHERE game_id = ? AND word = ?",
            (game_id, word)
        ).fetchone()
        if existing:
            raise ValueError(f"'{word}' já foi registrada com rank {existing['rank']}")
        self.db.execute(
            "INSERT INTO guesses(game_id, word, rank) VALUES (?, ?, ?)",
            (game_id, word, rank)
        )
        self.db.commit()

    def guesses(self, game_id: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT word, rank FROM guesses WHERE game_id = ? ORDER BY id", (game_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def finish(self, game_id: int, answer: str):
        answer = answer.strip().lower()
        if not answer or not answer.isalpha():
            raise ValueError("Digite a palavra secreta usando somente letras")
        # Se o jogo já teve a resposta inserida com outro rank, corrija para 1.
        self.db.execute(
            "INSERT INTO guesses(game_id, word, rank) VALUES (?, ?, 1) "
            "ON CONFLICT(game_id, word) DO UPDATE SET rank = 1",
            (game_id, answer)
        )
        self.db.execute(
            "UPDATE games SET answer = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (answer, game_id)
        )
        self.db.commit()

    def previous_examples(self) -> list[tuple[str, str, int, int]]:
        """(resposta, palpite, rank, id_partida) de partidas já encerradas."""
        rows = self.db.execute("""
            SELECT g.answer AS answer, p.word AS word, p.rank AS rank, g.id AS game_id
            FROM games g JOIN guesses p ON p.game_id = g.id
            WHERE g.finished_at IS NOT NULL AND g.answer IS NOT NULL
        """).fetchall()
        return [(r['answer'], r['word'], r['rank'], r['game_id']) for r in rows]

    def stats(self):
        rows = self.db.execute("""
            SELECT g.id, g.answer, COUNT(p.id) AS guesses
            FROM games g LEFT JOIN guesses p ON p.game_id = g.id
            WHERE g.finished_at IS NOT NULL GROUP BY g.id ORDER BY g.id DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.db.close()
