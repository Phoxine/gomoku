"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../src/app/static/game/game.js"), "utf8",
);
const id = "12345678-1234-4234-8234-123456789abc";

function state(stone = 0) {
  const board = Array.from({ length: 15 }, () => Array(15).fill(0));
  board[0][0] = stone;
  return { id, board, current_player: stone ? 2 : 1, status: "in_progress", winner: null };
}

function page({ saved = null, responder, clipboard }) {
  class Element {
    constructor(name) {
      this.children = [];
      this.listeners = {};
      this.classList = { toggle() {} };
      this.dataset = {};
      this.value = { "game-mode": "two_player", "forbidden-consequence": "warn" }[name] ?? "";
      this.textContent = "";
      this._disabled = false;
      this.tabIndex = 0;
    }
    get disabled() { return this._disabled; }
    set disabled(value) {
      this._disabled = value;
      if (value && document.activeElement === this) document.activeElement = null;
    }
    focus() {
      if (!this.disabled) {
        document.activeElement = this;
        this.listeners.focus?.();
      }
    }
    keydown(key) {
      let prevented = false;
      this.listeners.keydown?.({ key, preventDefault() { prevented = true; } });
      return prevented;
    }
    setAttribute(name, value) { this[name] = value; }
    appendChild(child) { this.children.push(child); }
    addEventListener(type, fn) { this.listeners[type] = fn; }
    click() { if (!this.disabled) return this.listeners.click?.(); }
  }
  class Dialog extends Element {
    open = false;

    showModal() {
      this.open = true;
      document.getElementById("forbidden-dismiss").focus();
    }

    close() {
      this.open = false;
      this.listeners.close?.();
    }
  }
  const elements = new Map();
  const document = {
    cookie: "",
    activeElement: null,
    getElementById(name) {
      if (!elements.has(name)) {
        elements.set(name, name === "forbidden-dialog" ? new Dialog() : new Element(name));
      }
      return elements.get(name);
    },
    createElement() { return new Element(); },
  };
  const values = new Map(saved ? [["gomoku.gameId", saved]] : []);
  const calls = [];
  const localStorage = {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
  };
  async function fetch(url, options = {}) {
    calls.push({ url, options });
    if (url === "/api/v1/csrf/") {
      document.cookie = "csrftoken=test-token";
      return { ok: true, json: async () => ({}) };
    }
    return responder(url, options);
  }
  vm.runInNewContext(source, {
    document, localStorage, fetch, navigator: { clipboard }, console,
  });
  return { document, elements, values, calls };
}

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function cpuState(revision) {
  const game = state();
  for (let index = 0; index < revision; index++) game.board[0][index] = index % 2 + 1;
  return { ...game, mode: "cpu", revision, current_player: revision % 2 ? 2 : 1 };
}

test("CPU mode renders the human move before requesting white and guards the board", async () => {
  let completeCpu;
  const app = page({
    responder(url) {
      if (url.endsWith("/moves/")) return response(cpuState(1));
      if (url.endsWith("/cpu-move/")) {
        const cells = app.elements.get("board").children;
        assert.equal(cells[0].className, "cell black");
        assert.equal(app.elements.get("status-text").textContent, "CPU to play (white)");
        return new Promise((resolve) => { completeCpu = resolve; });
      }
      return response(cpuState(0), 201);
    },
  });
  app.elements.get("game-mode").value = "cpu";
  await app.elements.get("new-game").click();
  assert.deepEqual(JSON.parse(app.calls.at(-1).options.body),
    { mode: "cpu", forbidden_move_policy: "off" });
  const cells = app.elements.get("board").children;
  cells[0].focus();
  const turn = cells[0].click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.calls.find(({ url }) => url.endsWith("/moves/")).options.body,
    '{"x":0,"y":0,"expected_revision":0}');
  assert.equal(app.calls.at(-1).options.body, '{"expected_revision":1}');
  assert.equal(app.calls.at(-1).options.headers["X-CSRFToken"], "test-token");
  assert.ok(cells.every((cell) => cell.disabled));
  const callCount = app.calls.length;
  cells[1].listeners.click();
  cells[0].keydown("ArrowRight");
  assert.equal(app.calls.length, callCount);
  completeCpu(response(cpuState(2)));
  await turn;
  assert.equal(cells[1].className, "cell white");
  assert.equal(app.elements.get("status-text").textContent, "Your turn (black)");
  assert.ok(cells.includes(app.document.activeElement));
  assert.equal(app.document.activeElement.disabled, false);
});

test("interrupted CPU advance keeps the saved board and retries from a fresh GET", async () => {
  let cpuPosts = 0;
  const app = page({
    saved: id,
    responder(url) {
      if (url.endsWith("/cpu-move/")) {
        cpuPosts++;
        return cpuPosts === 1 ? response({}, 500) : response(cpuState(2));
      }
      return response(cpuState(1));
    },
  });
  await new Promise((resolve) => setImmediate(resolve));
  const retry = app.elements.get("retry-turn");
  const cells = app.elements.get("board").children;
  assert.equal(cells[0].className, "cell black");
  assert.ok(cells.every((cell) => cell.disabled));
  assert.equal(retry.hidden, false);
  assert.match(app.elements.get("message").textContent, /interrupted/);
  retry.focus();
  await retry.click();
  assert.deepEqual(app.calls.slice(-2).map(({ url }) => url),
    [`/api/v1/games/${id}/`, `/api/v1/games/${id}/cpu-move/`]);
  assert.equal(cpuPosts, 2);
  assert.equal(retry.hidden, true);
  assert.equal(cells[1].className, "cell white");
  assert.ok(cells.includes(app.document.activeElement));
});

test("a warned forbidden move restores black's focus without advancing the CPU", async () => {
  const app = page({
    responder(url) {
      if (url.endsWith("/moves/")) {
        return response({ error: "forbidden_move", reason: "double_three" }, 409);
      }
      return response({ ...cpuState(0), forbidden_move_policy: "warn" }, 201);
    },
  });
  const { elements } = app;
  elements.get("game-mode").value = "cpu";
  const checkbox = elements.get("enable-forbidden-moves");
  checkbox.checked = true;
  checkbox.listeners.change();
  assert.equal(elements.get("forbidden-options").hidden, false);
  await elements.get("new-game").click();
  assert.deepEqual(JSON.parse(app.calls.at(-1).options.body),
    { mode: "cpu", forbidden_move_policy: "warn" });

  const cell = elements.get("board").children[224];
  cell.focus();
  await cell.click();
  assert.deepEqual(JSON.parse(app.calls.at(-1).options.body),
    { x: 14, y: 14, expected_revision: 0 });
  const dialog = elements.get("forbidden-dialog");
  assert.equal(dialog.open, true);
  assert.equal(elements.get("forbidden-title").textContent, "Forbidden move");
  assert.match(elements.get("forbidden-explanation").textContent, /Double-three/);
  assert.equal(app.document.activeElement, elements.get("forbidden-dismiss"));
  assert.equal(elements.get("message").textContent, "");
  assert.equal(elements.get("status-text").textContent, "Your turn (black)");
  assert.equal(cell.className, "cell");
  assert.ok(app.calls.every(({ url }) => !url.endsWith("/cpu-move/")));

  dialog.close();
  assert.equal(cell.disabled, false);
  assert.equal(app.document.activeElement, cell);
});

test("a forbidden loss stops play and reopens the saved white win details", async () => {
  const won = {
    ...cpuState(1), current_player: 1, status: "won", winner: 2,
    forbidden_move_policy: "loss", result_reason: "overline",
  };
  const app = page({
    responder(url, options) {
      if (url === "/api/v1/games/" && options.method === "POST") {
        return response({ ...cpuState(0), forbidden_move_policy: "loss" }, 201);
      }
      return response({ ...won });
    },
  });
  const { elements } = app;
  elements.get("game-mode").value = "cpu";
  elements.get("enable-forbidden-moves").checked = true;
  elements.get("forbidden-consequence").value = "loss";
  await elements.get("new-game").click();
  assert.deepEqual(JSON.parse(app.calls.at(-1).options.body),
    { mode: "cpu", forbidden_move_policy: "loss" });

  const board = elements.get("board");
  await board.children[0].click();
  const dialog = elements.get("forbidden-dialog");
  const details = elements.get("result-details");
  assert.equal(dialog.open, true);
  assert.equal(elements.get("forbidden-title").textContent, "White wins by forbidden move");
  assert.match(elements.get("forbidden-explanation").textContent, /Overline/);
  assert.equal(board.children[0].className, "cell black");
  assert.equal(board.dataset.currentPlayer, "");
  assert.ok(board.children.every((cell) => cell.disabled));
  assert.equal(details.hidden, false);
  dialog.close();
  assert.equal(app.document.activeElement, details);
  details.click();
  assert.equal(dialog.open, true);

  dialog.close();
  await elements.get("refresh-game").click();
  assert.equal(app.calls.at(-1).url, `/api/v1/games/${id}/`);
  assert.equal(dialog.open, true);
  assert.match(elements.get("forbidden-explanation").textContent, /Overline/);
  assert.ok(app.calls.every(({ url }) => !url.endsWith("/cpu-move/")));
});

test("retry after a committed CPU response was lost observes the new board without another POST", async () => {
  let stored = cpuState(1);
  const app = page({
    saved: id,
    responder(url) {
      if (url.endsWith("/cpu-move/")) {
        stored = cpuState(2);
        throw new Error("response lost");
      }
      return response(stored);
    },
  });
  await new Promise((resolve) => setImmediate(resolve));
  await app.elements.get("retry-turn").click();
  assert.equal(app.calls.filter(({ url }) => url.endsWith("/cpu-move/")).length, 1);
  assert.equal(app.elements.get("board").children[1].className, "cell white");
  assert.equal(app.elements.get("status-text").textContent, "Your turn (black)");
});

test("stale CPU response advances the newly observed pending revision", async () => {
  const revisions = [];
  const app = page({
    saved: id,
    responder(url, options) {
      if (url.endsWith("/cpu-move/")) {
        const { expected_revision } = JSON.parse(options.body);
        revisions.push(expected_revision);
        return response(cpuState(expected_revision === 1 ? 3 : 4));
      }
      return response(cpuState(1));
    },
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(revisions, [1, 3]);
  assert.equal(app.elements.get("status-text").textContent, "Your turn (black)");
  assert.equal(app.elements.get("board").children[3].className, "cell white");
});

test("lost human move response blocks placement until the saved game can be confirmed", async () => {
  let readable = false;
  const app = page({
    responder(url, options) {
      if (url === "/api/v1/games/") return response(cpuState(0), 201);
      if (url.endsWith("/moves/")) throw new Error("response lost");
      if (url.endsWith("/cpu-move/")) {
        assert.equal(options.body, '{"expected_revision":1}');
        return response(cpuState(2));
      }
      return readable ? response(cpuState(1)) : response({}, 500);
    },
  });
  app.elements.get("game-mode").value = "cpu";
  await app.elements.get("new-game").click();
  const cells = app.elements.get("board").children;
  await cells[0].click();
  assert.ok(cells.every((cell) => cell.disabled));
  assert.equal(app.elements.get("retry-turn").textContent, "Reload saved game");
  readable = true;
  await app.elements.get("retry-turn").click();
  assert.equal(cells[0].className, "cell black");
  assert.equal(cells[1].className, "cell white");
  assert.equal(cells[2].disabled, false);
});

for (const [mover, winner] of [["human", 1], ["CPU", 2], ["human", null]]) {
  test(`terminal ${mover} move renders ${winner ? "a win" : "a draw"} and ends placement`, async () => {
    const terminal = cpuState(mover === "CPU" ? 2 : 1);
    terminal.current_player = mover === "CPU" ? 2 : 1;
    terminal.status = winner ? "won" : "draw";
    terminal.winner = winner;
    const app = page({
      responder(url) {
        if (url.endsWith("/moves/")) return response(mover === "CPU" ? cpuState(1) : terminal);
        if (url.endsWith("/cpu-move/")) return response(terminal);
        return response(cpuState(0), 201);
      },
    });
    app.elements.get("game-mode").value = "cpu";
    await app.elements.get("new-game").click();
    const cells = app.elements.get("board").children;
    await cells[0].click();
    assert.ok(cells.every((cell) => cell.disabled));
    assert.equal(app.elements.get("status-text").textContent,
      winner === 2 ? "CPU wins!" : winner === 1 ? "You win!" : "It's a draw");
    assert.equal(app.calls.filter(({ url }) => url.endsWith("/cpu-move/")).length,
      mover === "CPU" ? 1 : 0);
  });
}

test("Copy ID points to the active game when clipboard writes are denied", async () => {
  const app = page({
    responder: () => response(state(), 201),
    clipboard: { async writeText() { throw new DOMException("Write denied.", "NotAllowedError"); } },
  });
  await app.elements.get("new-game").click();
  const pendingId = "87654321-4321-4321-8321-cba987654321";
  app.elements.get("game-id").value = pendingId;
  await app.elements.get("copy-id").click();

  assert.equal(app.elements.get("message").textContent, "Copy the game ID shown below the board.");
  assert.equal(app.elements.get("current-id").textContent, id);
  assert.equal(app.elements.get("game-id").value, pendingId);
});

test("Copy ID writes the current ID and confirms success", async () => {
  const writes = [];
  const app = page({
    responder: () => response(state(), 201),
    clipboard: { async writeText(value) { writes.push(value); } },
  });
  await app.elements.get("new-game").click();
  await app.elements.get("copy-id").click();

  assert.deepEqual(writes, [id]);
  assert.equal(app.elements.get("message").textContent, "Game ID copied.");
});

test("creates a game, stores it, and posts a move with CSRF", async () => {
  const app = page({
    responder(url) {
      if (url.endsWith("/moves/")) return response(state(1));
      return response(state(), 201);
    },
  });
  const board = app.elements.get("board");
  assert.equal(board.children.length, 225);
  assert.equal(board.children[0].disabled, true);
  assert.equal(board.dataset.currentPlayer, "");

  await app.elements.get("new-game").click();
  assert.deepEqual(JSON.parse(app.calls.at(-1).options.body),
    { mode: "two_player", forbidden_move_policy: "off" });
  assert.equal(app.values.get("gomoku.gameId"), id);
  assert.equal(app.elements.get("game-id").value, id);
  assert.equal(app.elements.get("status-text").textContent, "Black to play");
  assert.equal(board.dataset.currentPlayer, "1");
  assert.equal(board.children[0].disabled, false);

  board.children[0].click();
  await new Promise((resolve) => setImmediate(resolve));
  const move = app.calls.find((call) => call.url.endsWith("/moves/"));
  assert.equal(move.url, `/api/v1/games/${id}/moves/`);
  assert.equal(move.options.headers["X-CSRFToken"], "test-token");
  assert.equal(move.options.headers["Content-Type"], "application/json");
  assert.equal(move.options.body, '{"x":0,"y":0}');
  assert.equal(board.children[0].className, "cell black");
  assert.equal(board.children[0].disabled, true);
  assert.equal(app.elements.get("status-text").textContent, "White to play");
  assert.equal(board.dataset.currentPlayer, "2");
});

test("restores a saved game and preserves it when a move fails", async () => {
  const app = page({
    saved: id,
    responder(url) {
      if (url.endsWith("/moves/")) return response({ error: "occupied" }, 409);
      return response(state(1));
    },
  });
  // Initial restoration starts asynchronously as the script loads.
  await new Promise((resolve) => setImmediate(resolve));
  const board = app.elements.get("board");
  assert.equal(app.calls[0].url, `/api/v1/games/${id}/`);
  assert.equal(board.children[0].className, "cell black");
  assert.equal(app.elements.get("status-text").textContent, "White to play");

  board.children[1].click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.elements.get("message").textContent,
    "That intersection is already occupied. Refresh the game and try another.");
  assert.equal(board.children[0].className, "cell black");
  assert.equal(board.children[1].className, "cell");
  assert.equal(app.elements.get("status-text").textContent, "White to play");
  assert.equal(app.values.get("gomoku.gameId"), id);
});


test("arrow navigation skips occupied cells and stays within the board", async () => {
  const initial = state();
  initial.board[0][1] = 2;
  initial.board[1][2] = 1;
  for (let x = 3; x < 15; x++) initial.board[0][x] = 1;
  const app = page({ responder: () => response(initial, 201) });
  await app.elements.get("new-game").click();
  const cells = app.elements.get("board").children;
  cells[0].focus();
  assert.equal(app.document.activeElement, cells[0]);
  assert.equal(cells[0].keydown("ArrowRight"), true);
  assert.equal(app.document.activeElement, cells[2]);
  assert.deepEqual(cells.filter((cell) => cell.tabIndex === 0), [cells[2]]);
  assert.equal(cells[2].keydown("ArrowRight"), true);
  assert.equal(app.document.activeElement, cells[15]);
  assert.equal(cells[15].keydown("ArrowLeft"), true);
  assert.equal(app.document.activeElement, cells[2]);
  assert.equal(cells[2].keydown("ArrowDown"), true);
  assert.equal(app.document.activeElement, cells[32]);
  cells[0].focus();
  assert.equal(cells[0].keydown("ArrowUp"), true);
  assert.equal(app.document.activeElement, cells[0]);
  cells[224].focus();
  assert.equal(cells[224].keydown("ArrowRight"), true);
  assert.equal(app.document.activeElement, cells[224]);
});

test("keyboard move restores focus after pending success and failed moves", async () => {
  let resolveMove;
  let mode = "pending";
  const app = page({
    responder(url) {
      if (!url.endsWith("/moves/")) return response(state(), 201);
      if (mode === "pending") return new Promise((resolve) => { resolveMove = resolve; });
      return response({ error: "occupied" }, 409);
    },
  });
  await app.elements.get("new-game").click();
  const cells = app.elements.get("board").children;
  cells[0].focus();
  cells[0].click();
  // The CSRF fetch completes before the move request is issued.
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(cells[0].disabled, true);
  assert.equal(cells[1].disabled, true);
  assert.notEqual(app.document.activeElement, cells[0]);
  resolveMove(response(state(1)));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(cells[0].disabled, true);
  assert.ok(cells.includes(app.document.activeElement));
  assert.equal(app.document.activeElement.disabled, false);

  mode = "failure";
  const selected = app.document.activeElement;
  selected.click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.document.activeElement, selected);
  assert.equal(selected.disabled, false);
});

test("terminal move returns keyboard focus to New game", async () => {
  const won = state(1);
  won.status = "won";
  won.winner = 1;
  const app = page({
    responder(url) { return url.endsWith("/moves/") ? response(won) : response(state(), 201); },
  });
  await app.elements.get("new-game").click();
  const first = app.elements.get("board").children[0];
  first.focus();
  first.click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.elements.get("status-text").textContent, "Black wins!");
  assert.equal(app.document.activeElement, app.elements.get("new-game"));
});


test("a pending move does not steal focus after the player moves elsewhere", async () => {
  let resolveMove;
  const app = page({
    responder(url) {
      if (url.endsWith("/moves/")) return new Promise((resolve) => { resolveMove = resolve; });
      return response(state(), 201);
    },
  });
  await app.elements.get("new-game").click();
  const first = app.elements.get("board").children[0];
  first.focus();
  first.click();
  await new Promise((resolve) => setImmediate(resolve));
  const input = app.elements.get("game-id");
  input.focus();
  resolveMove(response(state(1)));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(app.document.activeElement, input);
});

test("horizontal navigation reaches the only other empty cell on a nearly full board", async () => {
  const nearlyFull = state();
  nearlyFull.board = Array.from({ length: 15 }, () => Array(15).fill(1));
  nearlyFull.board[0][0] = 0;
  nearlyFull.board[14][14] = 0;
  const app = page({ responder: () => response(nearlyFull, 201) });
  await app.elements.get("new-game").click();
  const cells = app.elements.get("board").children;
  cells[0].focus();
  cells[0].keydown("ArrowRight");
  assert.equal(app.document.activeElement, cells[224]);
  cells[224].keydown("ArrowRight");
  assert.equal(app.document.activeElement, cells[224]);
  cells[224].keydown("ArrowLeft");
  assert.equal(app.document.activeElement, cells[0]);
  cells[0].keydown("ArrowLeft");
  assert.equal(app.document.activeElement, cells[0]);
});
