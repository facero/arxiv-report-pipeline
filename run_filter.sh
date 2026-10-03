#!/bin/bash
# Wrapper to run embedding_filter.py in the arxiv conda env
# Usage: ./run_filter.sh --input papers/XXX.json --output scored/XXX_prefiltered.json --top 0.25

DIR="$(cd "$(dirname "$0")" && pwd)"
~/miniforge3/bin/conda run -n arxiv python3 "$DIR/embedding_filter.py" "$@"
