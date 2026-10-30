"""Jogue Contexto com sugestões por IA e rankings digitados manualmente."""
from __future__ import annotations
from pathlib import Path
from contexto_ai.database import Store
from contexto_ai.engine import SuggestionEngine
from contexto_ai.sample import OUR_GAME

ROOT = Path(__file__).resolve().parent


def ask_rank() -> int | None:
    while True:
        value = input("Rank no Contexto (1 = acertou; V = voltar): ").strip().lower()
        if value in {'v', 'voltar', 'sair'}:
            return None
        if value.isdigit() and int(value) >= 1:
            return int(value)
        print("Digite um inteiro positivo, por exemplo 16.")


def play(store: Store, engine: SuggestionEngine, game_id: int):
    while True:
        guesses = store.guesses(game_id)
        print("\n" + "=" * 52)
        print(f"PARTIDA #{game_id} — {len(guesses)} palpites registrados")
        if guesses:
            print("Melhores: " + ", ".join(
                f"{g['word']} ({g['rank']})" for g in sorted(guesses, key=lambda g: g['rank'])[:5]
            ))
        suggestions = engine.suggest(guesses, store.previous_examples())
        print("Sugestões: " + "  |  ".join(f"{i+1}. {w}" for i, w in enumerate(suggestions)))
        print("[Enter] usar sugestão 1 | [2-5] outra sugestão")
        print("Ou digite outra palavra | :fim para revelar a solução | :sair para salvar e voltar")
        raw = input("Sua próxima palavra: ").strip().lower()
        if raw in {":sair", ":voltar", ":menu"}:
            print("Partida salva automaticamente.")
            return
        if raw == ":fim":
            answer = input("Qual era a palavra secreta? ").strip().lower()
            try:
                store.finish(game_id, answer)
                print("Partida concluída e registrada! O histórico ajudará a calibrar futuros palpites.")
                return
            except ValueError as exc:
                print(exc)
                continue
        if raw == "":
            word = suggestions[0] if suggestions else None
        elif raw.isdigit() and 1 <= int(raw) <= len(suggestions):
            word = suggestions[int(raw)-1]
        else:
            word = raw
        if not word or not word.isalpha():
            print("Digite uma única palavra, apenas com letras.")
            continue
        if any(x['word'] == word for x in guesses):
            print("Essa palavra já foi testada nesta partida.")
            continue
        print(f"Palavra: {word}")
        rank = ask_rank()
        if rank is None:
            continue
        try:
            store.add_guess(game_id, word, rank)
        except ValueError as exc:
            print(exc)
            continue
        if rank == 1:
            store.finish(game_id, word)
            print(f"🎉 Acertou! Resposta: {word}. Partida salva no histórico.")
            return


def main():
    print("\n🧠 CONTEXTO AI — protótipo local\n")
    store = Store(ROOT / "dados" / "contexto.sqlite3")
    try:
        print("Carregando embeddings portugueses...")
        engine = SuggestionEngine(ROOT / "dados" / "cache")
        print(f"Pronto: {len(engine.words):,} palavras candidatas.")
        while True:
            active = store.active_game()
            print("\n=== MENU ===")
            if active is not None:
                print(f"1. Continuar partida #{active}")
                print("2. Nova partida")
            else:
                print("1. Nova partida")
                print("2. Importar nossa partida do chat (17 palavras)")
            print("3. Ver histórico e aprendizado")
            print("4. Sair")
            choice = input("Opção: ").strip()
            if choice == '1':
                play(store, engine, active if active is not None else store.new_game())
            elif choice == '2':
                if active is not None:
                    play(store, engine, store.new_game())
                else:
                    game_id = store.new_game()
                    for word, rank in OUR_GAME:
                        store.add_guess(game_id, word, rank)
                    print("Importados os 17 palpites reais desta conversa.")
                    play(store, engine, game_id)
            elif choice == '3':
                history = store.stats()
                if not history:
                    print("Nenhuma partida concluída ainda. Termine uma com :fim e a resposta secreta.")
                else:
                    print("\nPartidas concluídas:")
                    for row in history[:15]:
                        print(f"#{row['id']} — {row['answer']} — {row['guesses']} palavras registradas")
                calibration = engine.calibration(store.previous_examples())
                print("Calibração entre partidas: " + (
                    "ATIVA (regressão aprendida)" if calibration else
                    "ainda não ativa (precisa de >=3 partidas resolvidas e >=25 palpites válidos)"
                ))
                print("Obs.: calibração é experimental; não há garantia de melhorar o número de palpites.")
            elif choice == '4':
                print("Até a próxima!")
                break
            else:
                print("Opção inválida.")
    except (KeyboardInterrupt, EOFError):
        print("\nSaindo — dados já gravados.")
    finally:
        store.close()


if __name__ == '__main__':
    main()
