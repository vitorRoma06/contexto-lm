#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then
  python3 -m venv .venv
fi
if [ ! -f .venv/.instalado ]; then
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m spacy download pt_core_news_md
  touch .venv/.instalado
fi
.venv/bin/python app.py
