"use strict";

const app = document.getElementById("app");
const curtain = document.getElementById("curtain");
const curtainText = document.getElementById("curtain-text");
const curtainSub = document.getElementById("curtain-sub");
const curtainBtn = document.getElementById("curtain-btn");
const btnDownloadLog = document.getElementById("btn-download-log");
const btnNewGame = document.getElementById("btn-new-game");

const state = {
  serverState: null,
  orientation: 90, // 0=N, 90=E, 180=S, 270=W
  // Track what we've already revealed to the players so we know when to drop the curtain.
  lastRevealed: { phase: null, placing: null, current: null },
  pendingReveal: null, // { kind: "setup"|"battle", who: index, message }
};

function colLabel(index) {
  let label = "";
  let n = index;
  while (true) {
    label = String.fromCharCode(65 + (n % 26)) + label;
    n = Math.floor(n / 26) - 1;
    if (n < 0) return label;
  }
}

async function api(path, options = {}) {
  const opts = { headers: { "Content-Type": "application/json" }, ...options };
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || `HTTP ${res.status}`);
    err.payload = data;
    throw err;
  }
  return data;
}

function setState(serverState) {
  state.serverState = serverState;
  routeRender();
}

function showCurtain(text, sub, onReady) {
  curtainText.textContent = text;
  curtainSub.textContent = sub || "";
  curtain.classList.remove("hidden");
  curtainBtn.onclick = () => {
    curtain.classList.add("hidden");
    if (onReady) onReady();
  };
}

function hideCurtain() {
  curtain.classList.add("hidden");
  curtainBtn.onclick = null;
}

function buildGrid(parent, size, render) {
  parent.style.gridTemplateColumns = `repeat(${size + 1}, max-content)`;
  parent.replaceChildren();

  const corner = document.createElement("div");
  corner.className = "cell label";
  parent.appendChild(corner);
  for (let c = 0; c < size; c++) {
    const head = document.createElement("div");
    head.className = "cell label";
    head.textContent = colLabel(c);
    parent.appendChild(head);
  }
  for (let r = 0; r < size; r++) {
    const rowLabel = document.createElement("div");
    rowLabel.className = "cell label";
    rowLabel.textContent = String(r + 1);
    parent.appendChild(rowLabel);
    for (let c = 0; c < size; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.r = String(r);
      cell.dataset.c = String(c);
      render(cell, r, c);
      parent.appendChild(cell);
    }
  }
}

function applyMarker(cell, marker) {
  cell.classList.remove("water", "ship", "hit", "miss");
  switch (marker) {
    case ".":
      cell.classList.add("water");
      cell.textContent = "";
      break;
    case "S":
      cell.classList.add("ship");
      cell.textContent = "";
      break;
    case "X":
      cell.classList.add("hit");
      cell.textContent = "X";
      break;
    case "o":
      cell.classList.add("miss");
      cell.textContent = "o";
      break;
    default:
      cell.classList.add("water");
      cell.textContent = "";
  }
}

function shipPreviewCells(anchor, length, orientation, size) {
  const deltas = {
    0: [-1, 0],
    90: [0, 1],
    180: [1, 0],
    270: [0, -1],
  };
  const [dr, dc] = deltas[orientation] || [0, 1];
  const cells = [];
  for (let i = 0; i < length; i++) {
    const r = anchor[0] + dr * i;
    const c = anchor[1] + dc * i;
    cells.push([r, c]);
  }
  return cells;
}

function previewIsValid(cells, grid, size) {
  for (const [r, c] of cells) {
    if (r < 0 || c < 0 || r >= size || c >= size) return false;
    if (grid[r][c] !== ".") return false;
  }
  return true;
}

function renderNewGame() {
  const tpl = document.getElementById("tpl-new-game");
  app.replaceChildren(tpl.content.cloneNode(true));
  document.getElementById("new-game-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const form = ev.target;
    const names = [form.p1.value.trim(), form.p2.value.trim()];
    const data = await api("/api/new_game", { method: "POST", body: { names } });
    state.lastRevealed = { phase: null, placing: null, current: null };
    setState(data);
  });
}

function renderSetup() {
  const tpl = document.getElementById("tpl-setup");
  app.replaceChildren(tpl.content.cloneNode(true));
  const s = state.serverState;
  const setup = s.setup;
  const placingName = s.player_names[s.placing];

  document.getElementById("setup-title").textContent = `${placingName}, place your fleet`;

  const orientButtons = document.querySelectorAll(".orient-btn");
  orientButtons.forEach((btn) => {
    btn.classList.toggle("active", parseInt(btn.dataset.orient, 10) === state.orientation);
    btn.onclick = () => {
      state.orientation = parseInt(btn.dataset.orient, 10);
      renderSetup();
    };
  });

  document.getElementById("btn-rotate").onclick = () => {
    const seq = [0, 90, 180, 270];
    state.orientation = seq[(seq.indexOf(state.orientation) + 1) % 4];
    renderSetup();
  };

  document.getElementById("btn-auto").onclick = async () => {
    const data = await api("/api/auto_place", { method: "POST" });
    setState(data);
  };

  const finishBtn = document.getElementById("btn-finish");
  finishBtn.disabled = !setup.done;
  finishBtn.textContent =
    s.placing === 0 ? "Done — pass to next player" : "Done — start battle";
  finishBtn.onclick = async () => {
    const data = await api("/api/finish_setup", { method: "POST" });
    setState(data);
  };

  const shipInfo = document.getElementById("ship-info");
  if (setup.current_ship) {
    shipInfo.textContent = `${setup.current_ship.name} (length ${setup.current_ship.length})`;
  } else {
    shipInfo.textContent = "Fleet placed. Click Done to continue.";
  }

  const placed = document.getElementById("placed-list");
  placed.replaceChildren();
  for (const sh of setup.placed) {
    const li = document.createElement("li");
    li.textContent = sh.name;
    const span = document.createElement("span");
    span.textContent = `len ${sh.length}`;
    li.appendChild(span);
    placed.appendChild(li);
  }

  const remaining = document.getElementById("remaining-list");
  remaining.replaceChildren();
  for (const sh of setup.remaining) {
    const li = document.createElement("li");
    li.textContent = sh.name;
    const span = document.createElement("span");
    span.textContent = `len ${sh.length}`;
    li.appendChild(span);
    remaining.appendChild(li);
  }

  const grid = document.getElementById("setup-grid");
  buildGrid(grid, setup.size, (cell, r, c) => {
    applyMarker(cell, setup.grid[r][c]);
  });

  if (setup.current_ship) {
    const length = setup.current_ship.length;
    const size = setup.size;
    const cells = grid.querySelectorAll(".cell:not(.label)");
    cells.forEach((cell) => {
      const r = parseInt(cell.dataset.r, 10);
      const c = parseInt(cell.dataset.c, 10);
      cell.addEventListener("mouseenter", () => {
        const previewCells = shipPreviewCells([r, c], length, state.orientation, size);
        const ok = previewIsValid(previewCells, setup.grid, size);
        for (const [pr, pc] of previewCells) {
          if (pr < 0 || pc < 0 || pr >= size || pc >= size) continue;
          const idx = pr * size + pc;
          const target = cells[idx];
          if (!target) continue;
          target.classList.add(ok ? "preview-ok" : "preview-bad");
        }
      });
      cell.addEventListener("mouseleave", () => {
        cells.forEach((c2) => c2.classList.remove("preview-ok", "preview-bad"));
      });
      cell.addEventListener("click", async () => {
        try {
          const data = await api("/api/place_at", {
            method: "POST",
            body: { row: r, col: c, orientation: state.orientation },
          });
          setState(data);
        } catch (err) {
          flashError(err.message);
        }
      });
    });
  }
}

function renderBattle() {
  const tpl = document.getElementById("tpl-battle");
  app.replaceChildren(tpl.content.cloneNode(true));
  const s = state.serverState;
  const me = s.current;
  const opp = 1 - me;
  const myName = s.player_names[me];
  const oppName = s.player_names[opp];

  document.getElementById("battle-title").textContent = `${myName}, take your shot`;
  document.getElementById("opp-title").textContent = `${oppName}'s waters`;
  document.getElementById("own-title").textContent = `${myName}'s fleet`;

  const last = s.last_shot;
  const lastEl = document.getElementById("last-shot");
  if (last) {
    lastEl.classList.remove("hit", "miss", "sunk");
    let msg = `${last.shooter_name} fired at ${last.target_label} — `;
    if (last.outcome === "hit") {
      msg += "HIT.";
      lastEl.classList.add("hit");
    } else if (last.outcome === "sunk") {
      msg += `SUNK the ${last.sunk_ship}!`;
      lastEl.classList.add("sunk");
    } else if (last.outcome === "miss") {
      msg += "miss.";
      lastEl.classList.add("miss");
    } else {
      msg += last.outcome;
    }
    lastEl.textContent = msg;
  } else {
    lastEl.textContent = "";
  }

  const oppGrid = document.getElementById("opp-grid");
  oppGrid.classList.add("opp-clickable");
  buildGrid(oppGrid, s.size, (cell, r, c) => {
    applyMarker(cell, s.opponent_views[opp][r][c]);
  });
  oppGrid.querySelectorAll(".cell:not(.label)").forEach((cell) => {
    cell.addEventListener("click", async () => {
      const r = parseInt(cell.dataset.r, 10);
      const c = parseInt(cell.dataset.c, 10);
      const view = s.opponent_views[opp][r][c];
      if (view === "X" || view === "o") return;
      try {
        const data = await api("/api/shoot", {
          method: "POST",
          body: { row: r, col: c },
        });
        setState(data);
      } catch (err) {
        flashError(err.message);
      }
    });
  });

  const ownGrid = document.getElementById("own-grid");
  buildGrid(ownGrid, s.size, (cell, r, c) => {
    applyMarker(cell, s.boards[me][r][c]);
  });

  const fleet = document.getElementById("own-fleet");
  fleet.replaceChildren();
  for (const sh of s.fleets[me]) {
    const li = document.createElement("li");
    li.className = sh.sunk ? "sunk" : "";
    li.textContent = sh.name;
    const span = document.createElement("span");
    span.textContent = sh.sunk ? "sunk" : `len ${sh.length}`;
    li.appendChild(span);
    fleet.appendChild(li);
  }
}

function renderEnded() {
  const tpl = document.getElementById("tpl-ended");
  app.replaceChildren(tpl.content.cloneNode(true));
  const s = state.serverState;
  const winner = s.winner;
  const banner = document.getElementById("winner-banner");
  banner.textContent =
    winner === null
      ? "Game over"
      : `${s.player_names[winner]} wins!`;
  document.getElementById("end-name-0").textContent = s.player_names[0];
  document.getElementById("end-name-1").textContent = s.player_names[1];
  buildGrid(document.getElementById("end-grid-0"), s.size, (cell, r, c) => {
    applyMarker(cell, s.boards[0][r][c]);
  });
  buildGrid(document.getElementById("end-grid-1"), s.size, (cell, r, c) => {
    applyMarker(cell, s.boards[1][r][c]);
  });
  document.getElementById("btn-end-new").onclick = () => renderNewGame();
}

function flashError(message) {
  console.warn(message);
  const el = document.getElementById("last-shot");
  if (el) {
    el.textContent = message;
    el.classList.remove("hit", "miss", "sunk");
  } else {
    alert(message);
  }
}

function shouldShowCurtain() {
  const s = state.serverState;
  if (!s) return null;
  if (s.phase === "setup") {
    if (state.lastRevealed.phase !== "setup" || state.lastRevealed.placing !== s.placing) {
      return {
        text: `Pass the device to ${s.player_names[s.placing]}`,
        sub: "When you're alone with the screen, tap below to begin placement.",
        commit: () => {
          state.lastRevealed = {
            phase: "setup",
            placing: s.placing,
            current: null,
          };
        },
      };
    }
  }
  if (s.phase === "battle") {
    if (state.lastRevealed.phase !== "battle" || state.lastRevealed.current !== s.current) {
      return {
        text: `Pass the device to ${s.player_names[s.current]}`,
        sub: "When you're alone with the screen, tap below to take your shot.",
        commit: () => {
          state.lastRevealed = {
            phase: "battle",
            placing: null,
            current: s.current,
          };
        },
      };
    }
  }
  if (s.phase === "ended") {
    state.lastRevealed = { phase: "ended", placing: null, current: null };
  }
  return null;
}

function routeRender() {
  const s = state.serverState;
  if (!s || s.phase === "idle") {
    renderNewGame();
    return;
  }
  const reveal = shouldShowCurtain();
  if (reveal) {
    showCurtain(reveal.text, reveal.sub, () => {
      reveal.commit();
      routeRender();
    });
    return;
  }
  hideCurtain();
  if (s.phase === "setup") renderSetup();
  else if (s.phase === "battle") renderBattle();
  else if (s.phase === "ended") renderEnded();
}

btnDownloadLog.addEventListener("click", () => {
  window.location.href = "/api/log/download";
});

btnNewGame.addEventListener("click", () => {
  state.serverState = null;
  state.lastRevealed = { phase: null, placing: null, current: null };
  renderNewGame();
});

(async function init() {
  try {
    const s = await api("/api/state");
    if (!s || s.phase === "idle") {
      renderNewGame();
    } else {
      setState(s);
    }
  } catch (err) {
    renderNewGame();
  }
})();
