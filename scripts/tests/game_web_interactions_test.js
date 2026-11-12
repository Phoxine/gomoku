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
      this.disabled = false;
    }
    setAttribute(name, value) { this[name] = value; }
    appendChild(child) { this.children.push(child); }
    addEventListener(type, fn) { this.listeners[type] = fn; }
    click() { if (!this.disabled) return this.listeners.click?.(); }
  }
  const elements = new Map();
  const document = {
    cookie: "",
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
  return { elements, values, calls };
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

  await board.children[0].click();
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

  await board.children[1].click();
  assert.equal(app.elements.get("message").textContent,
    "That intersection is already occupied. Refresh the game and try another.");
  assert.equal(board.children[0].className, "cell black");
  assert.equal(board.children[1].className, "cell");
  assert.equal(app.elements.get("status-text").textContent, "White to play");
  assert.equal(app.values.get("gomoku.gameId"), id);
});
