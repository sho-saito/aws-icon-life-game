#!/usr/bin/env bash
# ゲーム起動スクリプト: venv 作成 → 依存インストール → main.py 実行
set -euo pipefail
cd "$(dirname "$0")"

# pygame 2.6.1 は Python 3.13 以下でしかビルド済み wheel が提供されていないため、
# 3.12 が見つかればそれを優先し、なければ python3 を使う。
find_python() {
  for candidate in python3.12 /opt/homebrew/opt/python@3.12/bin/python3.12 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
  echo "python3 が見つかりません" >&2
  exit 1
}

if [ ! -x venv/bin/python ]; then
  PY="$(find_python)"
  echo "venv を作成します ($PY)"
  "$PY" -m venv venv
fi

venv/bin/pip install -q -r requirements.txt
exec venv/bin/python main.py "$@"
