// Batch Maia queries through the WASM lc0 in headless Chromium.
//
// Usage:
//   tools/maia/setup.sh                                  (once per session)
//   node tools/maia/serve.mjs &                          (COOP/COEP server, port 8123)
//   NODE_PATH=/opt/node22/lib/node_modules node tools/maia/query.cjs job.json > maia.json
//
// job.json:  { "bands": [1100, 1500, 1900],
//              "positions": ["<FEN>", ...] }
// output:    { "1100": [ { "fen": ..., "bestmove": "e2e4", "value": 0.52,
//                          "moves": { "e2e4": 50.2, "d2d4": 23.3, ... } }, ... ],
//              "1500": [...], ... }
//
// `moves` maps UCI → probability (percent) that a human in that rating band
// plays the move; `value` is the expected score (0..1) for the side to move
// against human opposition at that band.
const { chromium } = require('playwright');
const { readFileSync } = require('fs');

(async () => {
  const job = JSON.parse(readFileSync(process.argv[2], 'utf8'));
  const port = process.env.MAIA_PORT ?? 8123;

  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('[page error]', e.message));

  await page.goto(`http://localhost:${port}/host.html`);
  await page.evaluate(() => window.maiaReady);
  const engineError = await page.evaluate(() => window.maiaError ?? null);
  if (engineError) throw new Error('engine failed to start: ' + engineError);

  const out = {};
  for (const band of job.bands) {
    await page.evaluate(b => window.maiaLoadNet(b), band);
    out[band] = [];
    for (const fen of job.positions) {
      const r = await page.evaluate(f => window.maiaQuery(f), fen);
      out[band].push({ fen, ...r });
    }
    console.error(`band ${band}: ${job.positions.length} positions done`);
  }

  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})();
