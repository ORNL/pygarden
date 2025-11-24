#!/usr/bin/env bash
# generate documentation for pygarden module

set -e
python scripts/gen_pygarden_docs.py
mkdocs build --clean