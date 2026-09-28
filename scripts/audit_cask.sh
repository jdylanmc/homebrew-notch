#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
  echo "This audit setup runs only on an ephemeral GitHub-hosted runner." >&2
  exit 1
fi

head="$(git rev-parse HEAD)"
[[ "$head" =~ ^[0-9a-f]{40}$ ]]
test -f Casks/notch-pocket.rb
taps="$(brew tap)"
if printf '%s\n' "$taps" | grep -Fxq jdylanmc/notch; then
  echo "Refusing to replace a pre-existing Homebrew tap." >&2
  exit 1
fi

brew tap --custom-remote jdylanmc/notch "$PWD"
tap_path="$(brew --repository jdylanmc/notch)"
test "$(git -C "$tap_path" rev-parse HEAD)" = "$head"
cmp Casks/notch-pocket.rb "$tap_path/Casks/notch-pocket.rb"
brew audit --cask --strict --online jdylanmc/notch/notch-pocket
