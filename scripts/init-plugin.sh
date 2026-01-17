#!/usr/bin/env bash

set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: ./scripts/init-plugin.sh --import-name rag2f_my_plugin --package-name rag2f-my-plugin [--description '...'] [--display-name '...']" >&2
  exit 2
fi

python3 scripts/init_plugin.py "$@"
