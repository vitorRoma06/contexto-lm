# Contexto AI 🧠

Protótipo de IA para jogar [Contexto](https://contexto.me/pt/) recebendo **manualmente** os rankings. Sugere palavras por proximidade semântica, guarda cada partida no SQLite e, após acumular dados, ajusta uma calibração estatística simples com os resultados de jogos anteriores.

## Como executar no Windows

1. Instale **Python 3.11 ou 3.12** de https://www.python.org/downloads/ se ainda não tiver. Durante a instalação marque **Add python.exe to PATH**.
2. Extraia todo o arquivo ZIP para uma pasta.
3. Clique duas vezes em **`iniciar_windows.bat`**.
4. Na primeira execução, o script instala bibliotecas e baixa o modelo de português do spaCy. Você precisa estar conectado à internet. Nas execuções seguintes, funciona localmente, sem API paga.
5. No menu, escolha **2 — Importar nossa partida do chat** (17 palpites reais) ou **1 — Nova partida**.
6. A IA sugere palavras. Teste uma no Contexto e **digite o ranking** retornado. Repita.
7. Quando descobrir a resposta (rank 1), ela é salva automaticamente. Se resolver fora do programa, use `:fim` e digite a palavra secreta.

**Importante:** a partida do chat ainda não tinha resposta final quando foi criada. Ela foi importada como *partida aberta*, com `poder = 16` e outros palpites. O sistema não inventa a resposta.

## Sem Windows

No macOS ou Linux, abra o terminal na pasta e rode `bash iniciar_mac_linux.sh` (Python 3.11 ou 3.12 recomendado).

## Como funciona, sem complicação

- `wordfreq` fornece palavras comuns em português.
- O `pt_core_news_md` do spaCy transforma palavras em vetores de 300 números (embeddings). O modelo é pré-treinado: não é necessário treinar a linguagem do zero.
- A IA pontua possíveis respostas por semelhança com seus melhores palpites e pela ordem dos rankings. **Esse ranking estimado é heurístico e não é o ranking real do Contexto.**
- `SQLite` mantém um registro local de cada palpite e da resposta final.
- **Após ao menos 3 partidas concluídas com 25 palpites válidos no total**, o programa ajusta uma regressão entre similaridade dos embeddings e rankings observados e usa essa relação para alterar as sugestões. Esse é um primeiro mecanismo de aprendizado entre partidas; ainda não é um modelo sofisticado nem garantia de melhoria.

## Comandos durante a partida

- **Enter**: usar a primeira sugestão.
- **2, 3, 4, 5**: escolher outra sugestão.
- **uma palavra**: enviar seu próprio palpite.
- **`:fim`**: informar a resposta secreta e concluir a partida.
- **`:sair`**: voltar ao menu mantendo os dados salvos.

O programa registra a palavra que você escolheu e o ranking digitado; ele **não acessa nem controla o site do Contexto**.

## Dados e privacidade

Dados ficam na pasta `dados/`, criada na execução. Para zerar o histórico, feche o programa e apague `dados/contexto.sqlite3`. A pasta `.venv/` contém as dependências instaladas; `dados/cache/` acelera o carregamento de embeddings. Nenhum arquivo dessas pastas precisa ser compartilhado.

## Limitações desta versão

- O vocabulário é um subconjunto das palavras portuguesas mais frequentes. A resposta do Contexto pode estar fora dele.
- Modelos semânticos diferentes discordam sobre o que é "próximo"; portanto, as sugestões podem ser ruins, mesmo com um ranking baixo.
- A calibração entre partidas é simples. Para avaliar melhorias de verdade, teremos de medir desempenho em partidas inéditas e comparar contra uma versão sem aprendizado.
- Não há automação de navegador, interface web, nuvem ou necessidade de chave de API.

## Arquivos principais

`app.py`: menus e interação pelo terminal.
`contexto_ai/engine.py`: embeddings, sugestões e calibração.
`contexto_ai/database.py`: armazenamento SQLite.
`contexto_ai/sample.py`: importação da nossa partida atual.

## Fontes

- spaCy Portuguese models: https://spacy.io/models/pt
- wordfreq: https://pypi.org/project/wordfreq/
