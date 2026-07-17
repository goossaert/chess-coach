// Browser half of the consolidated step-6 verification (see verify-game.py,
// which drives this as a single subprocess and merges the results with its
// python-chess checks). Loads the generated page once in headless Chromium and
// runs every in-page CLAUDE.md step-6 assertion against the window.__review
// hooks. Prints one JSON document to stdout:
//   { game: <the page's GAME object>, placement: <placement(total)>,
//     results: [{ name, pass, detail }], pageErrors: [...] }
//
// Usage: NODE_PATH=/opt/node22/lib/node_modules node tools/verify-game.cjs <page.html>
const { chromium } = require('playwright');
const { resolve } = require('node:path');

const page_path = process.argv[2];
if (!page_path) {
  console.error('usage: node tools/verify-game.cjs <page.html>');
  process.exit(2);
}

const results = [];
const check = (name, pass, detail = '') =>
  results.push(pass ? { name, pass: true } : { name, pass: false, detail: String(detail) });

(async () => {
const browser = await chromium.launch();
const page = await browser.newPage();
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));

await page.goto('file://' + resolve(page_path));
await page.waitForLoadState('load');

// Everything below runs in one evaluate so there is exactly one round trip
// into the page; the assertions themselves mirror CLAUDE.md step 6.
const out = await page.evaluate(() => {
  const R = window.__review;
  const results = [];
  const check = (name, pass, detail = '') =>
    results.push(pass ? { name, pass: true } : { name, pass: false, detail: String(detail) });
  const $ = id => document.getElementById(id);
  const hiddenOrAbsent = el => !el || el.hidden || el.offsetParent === null;

  const G = GAME;
  const has = fn => typeof R[fn] === 'function';   // hooks appear with their
                                                   // template version; a check
                                                   // whose hook is missing is
                                                   // skipped, not failed
  const total = R.total();
  const mistakes = G.mistakes || [];
  const isMaia = mistakes.some(m => m.humanBest) || (G.moveNotes || []).some(n => n.humanBest);
  const userPly = p => (G.playerColor === 'white') === (p % 2 === 0);

  // --- basics -------------------------------------------------------------
  check('error is null', R.error === null, R.error);
  check('error banner hidden', hiddenOrAbsent($('error-banner')));
  check('total() == movesSan.length', total === G.movesSan.length,
    `${total} vs ${G.movesSan.length}`);

  // --- mistake-card clicks ------------------------------------------------
  const cards = [...document.querySelectorAll('.mistake-card')];
  check('one card per mistake', cards.length === mistakes.length,
    `${cards.length} vs ${mistakes.length}`);
  const toggle = $('practice-first');
  if (toggle) toggle.checked = false;         // cards must jump, not retry
  mistakes.forEach((mk, i) => {
    if (!cards[i]) return;
    cards[i].click();
    check(`mistake ${i} click lands on ply ${mk.ply}`, R.getPly() === mk.ply, R.getPly());
    check(`mistake ${i} click activates panel`,
      $('fb-panel').classList.contains('mistake-active'));
  });

  // --- per-position stepping: arrows, legend, side-by-side ----------------
  // (moveNotes checks apply to pages that carry them — CLAUDE.md step 6)
  let stepFails = [], legendFails = [], humanFails = [], stackFails = [], noteFails = [];
  if ((G.moveNotes || []).length && has('noteAt'))
  for (let k = 0; k <= total; k++) {
    R.goTo(k);
    const note = k < total ? R.noteAt(k) : null;
    const isUser = k < total && userPly(k);
    if (isUser && !note) noteFails.push(k);
    const lines = [...document.querySelectorAll('#layer-arrows line.arrow')];
    const legendHidden = hiddenOrAbsent($('board-legend'));
    if (note) {
      const expected = 1 + (note.bestArrow ? 1 : 0) + (note.humanBestArrow ? 1 : 0);
      if (lines.length !== expected) stepFails.push(`ply ${k}: ${lines.length} arrows, expected ${expected}`);
      if (legendHidden) legendFails.push(`ply ${k}: legend hidden`);
      if (($('legend-played').textContent || '').trim() === 'played')
        legendFails.push(`ply ${k}: legend has no played SAN`);
      if (isMaia && isUser && hiddenOrAbsent($('legend-human')))
        humanFails.push(`ply ${k}: no human-findable legend`);
      if (isMaia && isUser && !note.humanBestArrow)
        humanFails.push(`ply ${k}: note lacks humanBestArrow`);
      const seen = new Set();
      for (const l of lines) {
        const key = ['x1', 'y1', 'x2', 'y2'].map(a => l.getAttribute(a)).join(',');
        if (seen.has(key)) stackFails.push(`ply ${k}: two arrows exactly stacked`);
        seen.add(key);
      }
    } else {
      if (lines.length) stepFails.push(`ply ${k}: ${lines.length} arrows on unannotated position`);
      if (!legendHidden) legendFails.push(`ply ${k}: legend visible without note`);
    }
  }
  if ((G.moveNotes || []).length && has('noteAt')) {
    check('every user ply annotated (moveNotes or mistakes)', !noteFails.length,
      'plies ' + noteFails.join(','));
    check('arrow count per position', !stepFails.length, stepFails.slice(0, 4).join(' | '));
    check('legend visibility per position', !legendFails.length, legendFails.slice(0, 4).join(' | '));
    if (isMaia)
      check('human-findable arrow+legend on every user move', !humanFails.length,
        humanFails.slice(0, 4).join(' | '));
    check('identical arrows render side by side, not stacked', !stackFails.length,
      stackFails.slice(0, 4).join(' | '));
  }

  // --- header strip iff fields --------------------------------------------
  check('strength line iff estimatedElo', hiddenOrAbsent($('head-strength')) === !G.estimatedElo);
  const hasStats = !!(G.accuracy || G.acpl || G.moveQuality);
  check('stat strip iff accuracy fields', hiddenOrAbsent($('head-stats')) === !hasStats);

  // --- per-mistake panel elements iff fields ------------------------------
  mistakes.forEach((mk, i) => {
    R.goTo(mk.ply);
    const panel = $('fb-panel');
    const has = sel => !!panel.querySelector(sel);
    check(`mistake ${i} typ-badge iff playedPopularity`, has('.typ-badge') === !!mk.playedPopularity);
    check(`mistake ${i} find-row iff bestFindability`, has('.find-row') === !!mk.bestFindability);
    check(`mistake ${i} win-row iff winBefore/After`, has('.win-row') === !!(mk.winBefore && mk.winAfter));
    check(`mistake ${i} drill-links iff drillLinks`,
      has('.drill-links') === !!(mk.drillLinks && mk.drillLinks.length));
    const card = cards[i];
    check(`mistake ${i} recur-tag iff recurrenceRisk`,
      !!card.querySelector('.recur-tag') === !!mk.recurrenceRisk);
    const chips = card.querySelectorAll('.tag-chip').length;
    check(`mistake ${i} tag chips match tags`, chips === (mk.tags || []).length,
      `${chips} vs ${(mk.tags || []).length}`);
  });

  // --- eval graph ----------------------------------------------------------
  if (G.evals && has('graphPly')) {
    check('eval graph visible', !hiddenOrAbsent($('eval-graph')));
    const poly = document.querySelector('#eval-graph polyline');
    const pts = poly ? poly.getAttribute('points').trim().split(/\s+/).length : 0;
    check('polyline has plies+1 points', pts === total + 1, `${pts} vs ${total + 1}`);
    const dots = [...document.querySelectorAll('#eval-graph .graph-dot')];
    const retryable = mistakes.filter(m => m.retry);
    check('one graph dot per mistake', dots.length === mistakes.length,
      `${dots.length} vs ${mistakes.length}`);
    if (dots.length) {
      R.goTo(0);
      dots[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
      const mk = mistakes.find(m => m.ply === Number(dots[0].dataset.ply)) || mistakes[0];
      check('graph dot click == mistake card click', R.getPly() === mk.ply &&
        $('fb-panel').classList.contains('mistake-active'), R.getPly());
      if (toggle && mk.retry) {
        toggle.checked = true;
        dots[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
        const st = R.retryState();
        check('graph dot respects practice-first (starts retry)',
          st && st.ply === mk.ply && st.status === 'await', JSON.stringify(st));
        toggle.checked = false;
        R.goTo(0);                       // cancel the retry
      }
    }
    const mid = Math.floor(total / 2);
    R.graphClick(mid);
    check('graphClick jumps the replay', R.getPly() === mid, R.getPly());
    R.goTo(3 <= total ? 3 : 0);
    check('graph cursor tracks the replay', R.graphPly() === R.getPly(),
      `${R.graphPly()} vs ${R.getPly()}`);
  } else {
    check('no eval graph without evals',
      !document.querySelector('#eval-graph svg') &&
      (!has('graphPly') || R.graphPly() === null));
  }

  // --- retry mode ----------------------------------------------------------
  const withRetry = has('retryState')
    ? mistakes.map((m, i) => [m, i]).filter(([m]) => m.retry) : [];
  const chipCount = document.querySelectorAll('.retry-chip').length;
  check('retry chips iff retry data', chipCount === withRetry.length,
    `${chipCount} vs ${withRetry.length}`);
  check('practice-first toggle iff retry data',
    hiddenOrAbsent($('practice-toggle')) === !withRetry.length);
  if (withRetry.length) {
    const [mk, i] = withRetry[0];
    const r = mk.retry;
    const wrong = r.legal.find(u => !r.solutions.includes(u) && !(r.acceptable || []).includes(u));

    R.retryStart(i);
    let st = R.retryState();
    check('retryStart enters await on the mistake ply',
      st && st.status === 'await' && st.ply === mk.ply, JSON.stringify(st));
    check('retry hides arrows', !document.querySelector('#layer-arrows line.arrow'));
    check('retry hides legend', hiddenOrAbsent($('board-legend')));

    R.retryPlay('e9e9');                 // illegal: must change nothing
    st = R.retryState();
    check('illegal move ignored', st && st.status === 'await' && st.attempts === 0,
      JSON.stringify(st));

    if (wrong) {
      R.retryPlay(wrong);
      st = R.retryState();
      check('first wrong move leaves one more try',
        st && st.status === 'await' && st.attempts === 1, JSON.stringify(st));
      R.retryPlay(wrong);
      st = R.retryState();
      check('second wrong move reveals', st && st.status === 'done' && st.outcome === 'revealed',
        JSON.stringify(st));
      check('revealed banner shown', !!document.querySelector('.retry-result.revealed'));
    }

    R.retryStart(i);
    R.retryPlay(r.solutions[0]);
    st = R.retryState();
    check('solution solves', st && st.status === 'done' && st.outcome === 'solved',
      JSON.stringify(st));
    check('solved banner shown', !!document.querySelector('.retry-result.solved'));
    check('feedback revealed after solve', $('fb-panel').classList.contains('mistake-active'));

    if ((r.acceptable || []).length) {
      R.retryStart(i);
      R.retryPlay(r.acceptable[0]);
      st = R.retryState();
      check('acceptable move grades acceptable',
        st && st.status === 'done' && st.outcome === 'acceptable', JSON.stringify(st));
    }

    R.retryStart(i);
    R.goTo(0);
    check('navigating away cancels the retry', R.retryState() === null);
  } else if (has('retryState')) {
    R.retryStart(0);
    check('retryStart is a no-op without retry data', R.retryState() === null);
  }

  // --- polish additions: highlights, opening report, time bar --------------
  const highlights = G.highlights || [];
  const hcards = [...document.querySelectorAll('.highlight-card')];
  check('one card per highlight', hcards.length === highlights.length,
    `${hcards.length} vs ${highlights.length}`);
  check('highlight section iff highlights',
    hiddenOrAbsent($('highlight-head')) === !highlights.length);
  highlights.forEach((hl, i) => {
    if (!hcards[i]) return;
    hcards[i].click();
    check(`highlight ${i} click lands on ply ${hl.ply}`, R.getPly() === hl.ply, R.getPly());
    check(`highlight ${i} click activates gold panel`,
      $('fb-panel').classList.contains('highlight-active'));
  });
  if (hcards.length) R.goTo(0);

  const orep = G.openingReport;
  check('opening report iff openingReport',
    hiddenOrAbsent($('opening-report')) === !(orep && (orep.note || orep.bookExitPly != null)));

  const hasTime = Array.isArray(G.timeSpent) && G.timeSpent.length === total && total > 0;
  check('time bar iff timeSpent', hiddenOrAbsent($('time-bar')) === !hasTime);
  if (hasTime) {
    const bars = [...document.querySelectorAll('#time-bar rect.tb')];
    check('one time-bar bar per half-move', bars.length === total, `${bars.length} vs ${total}`);
    if (bars.length) {
      R.goTo(0);
      bars[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
      check('time-bar click jumps the replay', R.getPly() === 1, R.getPly());
      R.goTo(0);
    }
  }

  return { game: G, placement: R.placement ? R.placement(total) : null, total, isMaia, results };
});

results.push(...out.results);
console.log(JSON.stringify({
  game: out.game, placement: out.placement, total: out.total,
  isMaia: out.isMaia, results, pageErrors,
}));
await browser.close();
})();
