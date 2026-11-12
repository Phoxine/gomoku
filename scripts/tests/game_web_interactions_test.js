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

function page({ saved = null, responder }) {
  class Element {
    constructor() {
      this.children = [];
      this.listeners = {};
      this.classList = { toggle() {} };
      this.value = "";
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
  const elements = new Map();
  const document = {
    cookie: "",
    activeElement: null,
    getElementById(name) {
      if (!elements.has(name)) elements.set(name, new Element());
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
  vm.runInNewContext(source, { document, localStorage, fetch, navigator: {}, console });
  return { document, elements, values, calls };
}

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

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

  await app.elements.get("new-game").click();
  assert.equal(app.values.get("gomoku.gameId"), id);
  assert.equal(app.elements.get("game-id").value, id);
  assert.equal(app.elements.get("status-text").textContent, "Black to play");
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
