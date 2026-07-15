// Static server for the Maia harness. The threaded WASM engine needs
// SharedArrayBuffer, which Chromium only enables on cross-origin-isolated
// pages — hence the COOP/COEP headers. Usage: node serve.mjs [port]
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const root = new URL('.', import.meta.url).pathname;
const port = Number(process.argv[2] ?? 8123);
const types = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.wasm': 'application/wasm',
  '.pb': 'application/octet-stream',
};

createServer((req, res) => {
  try {
    const rel = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (rel.includes('..')) throw new Error('bad path');
    const path = join(root, rel);
    const body = readFileSync(path);
    res.writeHead(200, {
      'Content-Type': types[extname(path)] ?? 'application/octet-stream',
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end('not found');
  }
}).listen(port, () => console.log(`maia harness serving on ${port}`));
