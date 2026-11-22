/*
 * game.js - screens and rules of Schrödinger's Cargo.
 * All quantum maths lives in qec.js; this file only handles turns, input and drawing.
 */
(function () {
  'use strict';
  const Q = window.QEC;
  const app = document.getElementById('app');
  const LETTERS = ['I', 'X', 'Y', 'Z'];
  const BLOCKS = [[0, 1, 2], [3, 4, 5], [6, 7, 8]];
  const CRATE_NAMES = ['A', 'B', 'C'];

  const G = {
    screen: 'title',
    players: ['Player 1', 'Player 2'],
    scores: [0, 0],
    rounds: 6,
    budget: 2,
    round: 0, // 0-based
    noise: null, // Noise player's error, array of 9 codes
    fix: null, // Decoder's correction
    cargo: null, // random secret qubit
    psi: null, // encoded state
    measured: null, // lamps after the error, measured on the simulated state
    history: [],
    lastWinner: -1,
  };

  const noiseIdx = () => G.round % 2;
  const decoderIdx = () => 1 - noiseIdx();
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const name = (i) => esc(G.players[i]);
  const lampsFor = (ops) => Q.measureLamps(Q.applyPauli(G.psi, ops));

  // ---------- Stabilizer group, used to show the simplest form of a leftover error ----------
  const GROUP = (() => {
    const out = [];
    for (let m = 0; m < 256; m++) {
      let p = new Array(9).fill(0);
      Q.CHECK_OPS.forEach((s, i) => { if ((m >> i) & 1) p = Q.multiply(p, s); });
      out.push(p);
    }
    return out;
  })();
  function simplest(p) {
    let best = p;
    for (const s of GROUP) {
      const c = Q.multiply(p, s);
      if (Q.weight(c) < Q.weight(best)) best = c;
    }
    return best;
  }
  function describe(p) {
    const parts = [];
    p.forEach((c, q) => { if (c) parts.push(`${LETTERS[c]}<sub>${q + 1}</sub>`); });
    return parts.length ? parts.join(' ') : 'nothing';
  }

  // ---------- Board ----------
  function qubitHTML(q, mode) {
    const op = mode === 'noise' ? G.noise[q] : mode === 'decode' ? G.fix[q] : Q.multiply(G.noise, G.fix)[q];
    const letter = LETTERS[op];
    let controls = '';
    if (mode === 'noise' || mode === 'decode') {
      const arr = mode === 'noise' ? G.noise : G.fix;
      const full = mode === 'noise' && Q.weight(G.noise) >= G.budget && !arr[q];
      controls = `<div class="switches" role="group" aria-label="Qubit ${q + 1}">` +
        LETTERS.map((L, c) => `<button class="sw ${L} ${arr[q] === c ? 'on' : ''}" data-action="set" data-q="${q}" data-c="${c}"
          ${full && c ? 'disabled title="Budget used up"' : ''} aria-pressed="${arr[q] === c}">${L}</button>`).join('') + '</div>';
    } else {
      const n = LETTERS[G.noise[q]], f = LETTERS[G.fix[q]];
      controls = `<div class="chips"><span class="chip ${n}" title="Noise">N:${n}</span><span class="chip ${f}" title="Fix">F:${f}</span></div>`;
    }
    const delay = mode === 'reveal' ? `style="animation-delay:${0.08 * q}s"` : '';
    return `<div class="qubit op-${letter}" ${delay}>
      <div class="orb" id="orb${q}"><span class="orb-letter">${letter === 'I' ? '' : letter}</span><span class="orb-name">q${q + 1}</span></div>
      ${controls}
    </div>`;
  }

  function boardHTML(mode, lamps) {
    let h = `<div class="board ${mode === 'reveal' ? 'reveal' : ''}">`;
    BLOCKS.forEach((qs, b) => {
      h += `<div class="crate"><div class="crate-label">Crate ${CRATE_NAMES[b]}</div>`;
      qs.forEach((q, j) => {
        h += qubitHTML(q, mode);
        if (j < 2) {
          const ci = b * 2 + j;
          h += `<div class="zlamp ${lamps[ci] ? 'lit' : ''}" title="Bit check Z${q + 1}Z${q + 2}: lights if q${q + 1} and q${q + 2} disagree">
            <span class="bulb"></span><span class="lamp-text">q${q + 1}·q${q + 2}</span></div>`;
        }
      });
      h += '</div>';
      if (b < 2) {
        const ci = 6 + b;
        h += `<div class="xlamp ${lamps[ci] ? 'lit' : ''}" title="Phase check: lights if crates ${CRATE_NAMES[b]} and ${CRATE_NAMES[b + 1]} disagree in phase">
          <span class="bulb"></span><span class="lamp-text">phase<br>${CRATE_NAMES[b]}|${CRATE_NAMES[b + 1]}</span></div>`;
      }
    });
    return h + '</div>';
  }

  function readoutHTML(lamps) {
    return `<div class="readout" aria-label="Measured lamps">${lamps.map((v, i) =>
      `<span class="dot ${i < 6 ? 'zc' : 'xc'} ${v ? 'on' : ''}"></span>`).join('')}</div>`;
  }

  function topbar() {
    const n = noiseIdx(), d = decoderIdx();
    const s = (i) => `<div class="score ${G.lastWinner === i && G.screen === 'reveal' ? 'bump' : ''}">
      <span>${name(i)}</span><span class="role ${i === n ? 'noise' : 'decoder'}">${i === n ? 'Noise' : 'Decoder'}</span><b>${G.scores[i]}</b></div>`;
    return `<div class="topbar"><span class="round-pill">Round ${G.round + 1} of ${G.rounds} · budget ${G.budget}</span>
      <div class="scores">${s(0)}${s(1)}</div></div>`;
  }

  // ---------- Screens ----------
  const CRATE_SVG = `<svg viewBox="0 0 240 220" class="float" aria-hidden="true">
    <defs><linearGradient id="cg" x1="0" x2="1"><stop offset="0" stop-color="#6c7bff"/><stop offset="1" stop-color="#c46bff"/></linearGradient></defs>
    <polygon points="120,20 220,70 120,120 20,70" fill="#2b3a7a" stroke="url(#cg)" stroke-width="3"/>
    <polygon points="20,70 120,120 120,205 20,155" fill="#1c2756" stroke="url(#cg)" stroke-width="3"/>
    <polygon points="220,70 120,120 120,205 220,155" fill="#151d44" stroke="url(#cg)" stroke-width="3"/>
    <text x="70" y="158" font-size="44" fill="#ff8a3d" font-family="monospace" font-weight="700">?</text>
    <text x="150" y="158" font-size="44" fill="#4da3ff" font-family="monospace" font-weight="700">?</text>
    <circle cx="120" cy="70" r="16" fill="#c46bff"><animate attributeName="r" values="12;18;12" dur="3s" repeatCount="indefinite"/></circle>
  </svg>`;

  function titleScreen() {
    return `<section class="screen title-wrap">
      <div>
        <div class="logo">Schrödinger's <span class="ket">|Cargo⟩</span></div>
        <p class="tagline">A two-player, pass-the-computer game about quantum error correction. One of you is the <b>Noise</b>, secretly flipping qubits. The other is the <b>Decoder</b>, who can only see the warning lamps. Can you keep the cargo alive?</p>
        <div class="panel setup">
          <div class="two">
            <div><label for="p1">Player 1</label><input id="p1" maxlength="16" value="${esc(G.players[0])}"></div>
            <div><label for="p2">Player 2</label><input id="p2" maxlength="16" value="${esc(G.players[1])}"></div>
          </div>
          <div class="two">
            <div><label for="rounds">Rounds (roles swap each round)</label>
              <select id="rounds">${[2, 4, 6, 8, 10].map((r) => `<option ${r === G.rounds ? 'selected' : ''}>${r}</option>`).join('')}</select></div>
            <div><label for="budget">Noise budget (qubits per round)</label>
              <select id="budget">
                <option value="1" ${G.budget === 1 ? 'selected' : ''}>1 · tutorial (always fixable)</option>
                <option value="2" ${G.budget === 2 ? 'selected' : ''}>2 · classic</option>
                <option value="3" ${G.budget === 3 ? 'selected' : ''}>3 · chaos</option>
              </select></div>
          </div>
          <div class="row" style="margin-top:18px">
            <button class="btn primary big" data-action="start">Start game</button>
            <button class="btn ghost" data-action="rules">How to play</button>
            <a class="btn ghost" href="handout.html" target="_blank" style="text-decoration:none">Handout</a>
          </div>
        </div>
      </div>
      <div class="hero-art">${CRATE_SVG}</div>
    </section>`;
  }

  function passScreen(toIdx, role, next) {
    const other = 1 - toIdx;
    const msg = role === 'Noise'
      ? `You will secretly corrupt the cargo. <b>${name(other)}</b>, look away!`
      : `The cargo has been tampered with. <b>${name(other)}</b>, hands off the keyboard!`;
    return `<section class="screen">${topbar()}
      <div class="curtain"><div>
        <div class="lock">🔒</div>
        <p class="muted">Pass the computer to</p>
        <h1><span class="who">${name(toIdx)}</span> · the ${role}</h1>
        <p>${msg}</p>
        <button class="btn primary big" data-action="${next}">I'm ${name(toIdx)}, show my screen</button>
      </div></div></section>`;
  }

  function noiseScreen() {
    const used = Q.weight(G.noise);
    const lamps = lampsFor(G.noise);
    const coins = Array.from({ length: G.budget }, (_, i) => `<span class="coin ${i < used ? 'used' : ''}"></span>`).join('');
    return `<section class="screen">${topbar()}
      <div class="stage-head"><div><h2>😈 ${name(noiseIdx())}, inject some noise</h2>
        <p>Flip up to ${G.budget} qubit${G.budget > 1 ? 's' : ''}. You can see the lamps your errors will light. That's all the Decoder will see. Can you make them lie?</p></div>
        <div class="budget" id="budget" aria-label="Budget">${coins}<span class="muted">${used}/${G.budget} used</span></div></div>
      ${boardHTML('noise', lamps)}
      <div class="row center">
        <button class="btn ghost" data-action="clear">Clear</button>
        <button class="btn primary big" data-action="seal">Seal the cargo 🔒</button>
      </div></section>`;
  }

  const CHEAT = `<div class="panel cheat"><h3>Lamp cheat-sheet (one error)</h3>
    <table>
      <tr><td><span class="lamp-dot zc"></span> q1·q2 only</td><td>bit flip on q1</td></tr>
      <tr><td><span class="lamp-dot zc"></span><span class="lamp-dot zc"></span> q1·q2 + q2·q3</td><td>bit flip on q2</td></tr>
      <tr><td><span class="lamp-dot zc"></span> q2·q3 only</td><td>bit flip on q3</td></tr>
      <tr><td colspan="2" class="muted">(same pattern in crates B and C)</td></tr>
      <tr><td><span class="lamp-dot xc"></span> A|B only</td><td>phase flip somewhere in crate A</td></tr>
      <tr><td><span class="lamp-dot xc"></span><span class="lamp-dot xc"></span> both</td><td>phase flip in crate B</td></tr>
      <tr><td><span class="lamp-dot xc"></span> B|C only</td><td>phase flip in crate C</td></tr>
      <tr><td>orange + blue</td><td>maybe one <span class="tag y">Y</span> on the same qubit</td></tr>
    </table>
    <p class="muted" style="font-size:.85rem;margin-bottom:0">A phase flip can be fixed with Z on <i>any</i> qubit of the right crate. Quantum codes are forgiving like that.</p></div>`;

  function decodeScreen() {
    const lamps = Q.syndrome(G.fix).map((v, i) => v ^ G.measured[i]); // = lamps of (noise x fix)
    const allDark = lamps.every((v) => !v);
    return `<section class="screen">${topbar()}
      <div class="stage-head"><div><h2>🛰️ ${name(decoderIdx())}, rescue the cargo</h2>
        <p>The lamps were measured after Noise struck. Flip switches to apply fixes: the lamps show what they would read after your fix. Dark lamps are necessary, but not always enough!</p></div>
        <div><span class="muted" style="font-size:.8rem">Original readout</span>${readoutHTML(G.measured)}</div></div>
      <div class="cols"><div>${boardHTML('decode', lamps)}
        <div class="row center">
          <button class="btn ghost" data-action="clearfix">Reset fixes</button>
          <button class="btn primary big" data-action="ship">${allDark ? 'Ship it 🚀' : 'Ship it anyway ⚠️'}</button>
        </div>
        ${allDark ? '' : '<p class="center muted" style="margin-top:10px">Some lamps are still lit. Shipping now means the cargo is still corrupted.</p>'}
      </div>${CHEAT}</div></section>`;
  }

  function revealScreen() {
    const residual = Q.multiply(G.noise, G.fix);
    const v = Q.classify(residual);
    const after = Q.applyPauli(Q.applyPauli(G.psi, G.noise), G.fix);
    const f = Q.fidelity(G.psi, after);
    const minF = Math.min(...Q.cardinalFidelities(residual).map((c) => c.f));
    const simple = simplest(residual);
    const finalLamps = Q.measureLamps(after);
    let title, text;
    if (v.safe) {
      title = '📦 Cargo delivered safely!';
      if (Q.weight(residual) === 0) text = `The fix undid the noise exactly.`;
      else text = `The leftover error ${describe(residual)} is one of the code's own checks (a <b>stabilizer</b>), so it does nothing at all to the cargo. You didn't need to find the exact error, just the right <i>class</i> of error. That's degeneracy, a purely quantum bonus.`;
      if (Q.weight(G.noise) === 0) text = `Noise held back this round, and the Decoder didn't break anything.`;
    } else if (v.lit) {
      title = '💥 Cargo corrupted';
      text = `Lamps were still lit when the cargo shipped, so the state was outside the protected code space. Fidelity with the original cargo is 0.`;
    } else {
      const what = { X: 'its bit (|0⟩ ↔ |1⟩)', Z: 'its phase (|+⟩ ↔ |−⟩)', Y: 'both its bit and phase' }[v.logical];
      title = '🕳️ Cargo silently flipped!';
      text = `Every lamp went dark, but the leftover error ${describe(simple)} is a <b>logical ${v.logical}</b>: it flips ${what} without lighting any lamp. Noise's error plus the fix added up to an undetectable change.`;
    }
    const winner = v.safe ? decoderIdx() : noiseIdx();
    return `<section class="screen">${topbar()}
      <div class="stage-head"><div><h2>The reveal</h2><p>N = Noise's error, F = Decoder's fix. Each orb shows what's left over.</p></div></div>
      ${boardHTML('reveal', finalLamps)}
      <div class="verdict ${v.safe ? 'safe' : 'lost'}">
        <h2>${title}</h2>
        <p>${text}</p>
        <p><b>${name(winner)}</b> scores as ${v.safe ? 'Decoder' : 'Noise'}.</p>
        <div class="facts">
          <div class="fact"><div class="k">Noise injected</div><div class="v">${describe(G.noise)}</div></div>
          <div class="fact"><div class="k">Decoder fixed</div><div class="v">${describe(G.fix)}</div></div>
          <div class="fact"><div class="k">This round's secret cargo · fidelity</div><div class="v">${(100 * f).toFixed(1)}%</div><div class="fbar"><i style="width:${100 * f}%"></i></div></div>
          <div class="fact"><div class="k">Worst of 6 test cargos</div><div class="v">${(100 * minF).toFixed(1)}%</div><div class="fbar"><i style="width:${100 * minF}%"></i></div></div>
        </div>
      </div>
      <div class="row center"><button class="btn primary big" data-action="next">${G.round + 1 >= G.rounds ? 'Final scores 🏆' : 'Next round · swap roles'}</button></div>
    </section>`;
  }

  function finalScreen() {
    const [a, b] = G.scores;
    const w = a === b ? -1 : a > b ? 0 : 1;
    const head = w < 0 ? `It's a draw. A superposition of winners!` : `${name(w)} wins!`;
    const rows = G.history.map((h, i) => `<tr><td>${i + 1}</td><td>${name(h.noise)}</td><td>${name(h.decoder)}</td>
      <td class="mono">${h.noiseStr}</td><td class="mono">${h.fixStr}</td><td class="${h.safe ? 'win' : 'lose'}">${h.safe ? 'saved' : h.logical ? 'logical ' + h.logical : 'corrupted'}</td></tr>`).join('');
    const saves = [0, 1].map((i) => G.history.filter((h) => h.decoder === i && h.safe).length);
    const asDec = [0, 1].map((i) => G.history.filter((h) => h.decoder === i).length);
    return `<section class="screen center">
      <div class="trophy">${w < 0 ? '⚖️' : '🏆'}</div>
      <h1 style="font-size:clamp(2rem,5vw,3rem)">${head}</h1>
      <p class="muted">${name(0)} ${a} : ${b} ${name(1)}</p>
      <div class="facts" style="max-width:640px;margin:0 auto 18px">
        ${[0, 1].map((i) => `<div class="fact"><div class="k">${name(i)} as Decoder</div><div class="v">${saves[i]}/${asDec[i]} cargos saved</div></div>`).join('')}
      </div>
      <div class="panel" style="text-align:left;overflow-x:auto"><table class="history">
        <tr><th>#</th><th>Noise</th><th>Decoder</th><th>Errors</th><th>Fixes</th><th>Result</th></tr>${rows}</table></div>
      <div class="row center" style="margin-top:18px">
        <button class="btn primary big" data-action="rematch">Rematch</button>
        <button class="btn ghost" data-action="home">New players</button>
      </div></section>`;
  }

  // ---------- Flow ----------
  function newRound() {
    G.noise = new Array(9).fill(0);
    G.fix = new Array(9).fill(0);
    G.cargo = Q.randomCargo();
    G.psi = Q.encode(G.cargo.a, G.cargo.b);
    G.measured = null;
    G.lastWinner = -1;
    G.screen = 'passNoise';
  }

  let lastScreen = null;
  function render() {
    let h = '';
    switch (G.screen) {
      case 'title': h = titleScreen(); break;
      case 'passNoise': h = passScreen(noiseIdx(), 'Noise', 'show-noise'); break;
      case 'noise': h = noiseScreen(); break;
      case 'passDecoder': h = passScreen(decoderIdx(), 'Decoder', 'show-decode'); break;
      case 'decode': h = decodeScreen(); break;
      case 'reveal': h = revealScreen(); break;
      case 'final': h = finalScreen(); break;
    }
    document.querySelectorAll('.confetti').forEach((c) => c.remove());
    const same = G.screen === lastScreen;
    const y = window.scrollY;
    app.innerHTML = h;
    // Editing a switch re-draws the same screen: keep scroll and skip the entrance animation.
    if (same) { app.querySelectorAll('.screen').forEach((el) => el.classList.add('still')); window.scrollTo({ top: y }); }
    else window.scrollTo({ top: 0 });
    lastScreen = G.screen;
  }

  function confetti() {
    const box = document.createElement('div');
    box.className = 'confetti';
    const cols = ['#ff8a3d', '#4da3ff', '#c46bff', '#3ee08f', '#ffffff'];
    for (let i = 0; i < 80; i++) {
      const p = document.createElement('i');
      p.style.left = Math.random() * 100 + 'vw';
      p.style.background = cols[i % cols.length];
      p.style.animationDuration = 1.8 + Math.random() * 1.8 + 's';
      p.style.animationDelay = 1.9 + Math.random() * 0.6 + 's';
      box.appendChild(p);
    }
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 6000);
  }

  // Re-render only the board area while editing, keeping the "pop" animation on the changed orb.
  function rerenderKeep(q) {
    render();
    const orb = document.getElementById('orb' + q);
    if (orb) orb.classList.add('pop');
  }

  app.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-action]');
    if (!btn) return;
    const a = btn.dataset.action;
    if (a === 'rules') { document.getElementById('rules').hidden = false; return; }
    if (a === 'start') {
      G.players = [document.getElementById('p1').value.trim() || 'Player 1', document.getElementById('p2').value.trim() || 'Player 2'];
      G.rounds = +document.getElementById('rounds').value;
      G.budget = +document.getElementById('budget').value;
      G.scores = [0, 0]; G.round = 0; G.history = [];
      newRound();
    } else if (a === 'show-noise') {
      G.screen = 'noise';
    } else if (a === 'set') {
      const q = +btn.dataset.q, c = +btn.dataset.c;
      if (G.screen === 'noise') {
        if (c && !G.noise[q] && Q.weight(G.noise) >= G.budget) {
          const b = document.getElementById('budget');
          b.classList.remove('shake'); void b.offsetWidth; b.classList.add('shake');
          return;
        }
        G.noise[q] = c;
      } else {
        G.fix[q] = c;
      }
      rerenderKeep(q);
      return;
    } else if (a === 'clear') {
      G.noise.fill(0);
    } else if (a === 'clearfix') {
      G.fix.fill(0);
    } else if (a === 'seal') {
      // Measure the 8 checks on the simulated, corrupted state. This is all the Decoder gets.
      G.measured = lampsFor(G.noise);
      G.screen = 'passDecoder';
    } else if (a === 'show-decode') {
      G.screen = 'decode';
    } else if (a === 'ship') {
      const v = Q.classify(Q.multiply(G.noise, G.fix));
      const winner = v.safe ? decoderIdx() : noiseIdx();
      G.scores[winner]++;
      G.lastWinner = winner;
      G.history.push({
        noise: noiseIdx(), decoder: decoderIdx(), safe: v.safe, logical: !v.lit && !v.safe ? v.logical : null,
        noiseStr: Q.toStr(G.noise).replace(/I/g, '·'), fixStr: Q.toStr(G.fix).replace(/I/g, '·'),
      });
      G.screen = 'reveal';
      render();
      if (v.safe) confetti();
      return;
    } else if (a === 'next') {
      G.round++;
      if (G.round >= G.rounds) { G.round--; G.screen = 'final'; } else newRound();
    } else if (a === 'rematch') {
      G.scores = [0, 0]; G.round = 0; G.history = []; newRound();
    } else if (a === 'home') {
      G.screen = 'title';
    }
    render();
  });

  document.getElementById('rules').addEventListener('click', (ev) => {
    if (ev.target.closest('[data-action="close-rules"]') || ev.target.id === 'rules') document.getElementById('rules').hidden = true;
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') document.getElementById('rules').hidden = true;
  });

  // Expose for automated browser tests only.
  window.__cargo = G;
  render();
})();
