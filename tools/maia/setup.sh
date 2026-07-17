#!/usr/bin/env bash
# One-time per-session setup for the Maia human-model pass (CLAUDE.md step 2b).
# Fetches the zerofish WASM engine (lc0 + stockfish) from npm and the Maia-1
# rating-band networks from the CSSLab GitHub repo, then applies a small patch
# to the minified engine. Everything lands in vendor/ and weights/ (gitignored).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor weights

# 1. zerofish: WASM lc0 with a UCI interface, runs in Chromium.
#    (npm chatter captured; shown only if the pack fails)
if [ ! -f vendor/package/dist/zerofishEngine.js ]; then
  if ! out=$(npm pack zerofish@0.0.36 --pack-destination vendor 2>&1); then
    echo "$out" >&2; exit 1
  fi
  tar -xzf vendor/zerofish-0.0.36.tgz -C vendor
fi

# 2. Patch: on engine errors the minified build calls the Module callback `qb`,
#    which is never defined inside its pthread workers — the tab dies with
#    "h.qb is not a function" before the real error is reported. Fall back to
#    console.error so errors surface instead of crashing the page.
python3 - <<'EOF'
path = 'vendor/package/dist/zerofishEngine.js'
src = open(path).read()
broken = 'function vb(a){h.qb(a?R(t,a):"")}'
patched = 'function vb(a){(h.qb||console.error)(a?R(t,a):"")}'
if broken in src:
    open(path, 'w').write(src.replace(broken, patched))
elif patched in src:
    pass
else:
    raise SystemExit('patch target not found — zerofish version changed? '
                     'Look for the h.qb error callback and adapt the patch.')
EOF

# 3. Maia-1 rating-band networks (CSSLab). lc0's setZeroWeights wants the raw
#    protobuf, so gunzip. ~1.7 MB per band.
for elo in 1100 1200 1300 1400 1500 1600 1700 1800 1900; do
  [ -f "weights/maia-$elo.pb" ] && continue
  curl -sL --fail --max-time 120 \
    "https://raw.githubusercontent.com/CSSLab/maia-chess/master/maia_weights/maia-$elo.pb.gz" \
    -o "weights/maia-$elo.pb.gz"
  gunzip -f "weights/maia-$elo.pb.gz"
done

echo "maia setup complete"
