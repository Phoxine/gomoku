(() => {
  "use strict";
  const board = document.getElementById("board");
  const message = document.getElementById("message");
  const idInput = document.getElementById("game-id");
  const currentId = document.getElementById("current-id");
  const newButton = document.getElementById("new-game");
  const loadButton = document.getElementById("load-game");
  const refreshButton = document.getElementById("refresh-game");
  const copyButton = document.getElementById("copy-id");
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  let game = null;
  let busy = false;
  let csrfReady = false;
  const cells = [];
  let focusedCell = 0;

  function cookie(name) {
    const value = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
    return value ? decodeURIComponent(value.slice(name.length + 1)) : "";
  }

  function remember(id) {
    try { localStorage.setItem("gomoku.gameId", id); } catch (_) { /* Storage is optional. */ }
  }

  function remembered() {
    try { return localStorage.getItem("gomoku.gameId"); } catch (_) { return null; }
  }

  async function request(url, options = {}) {
    if (options.method === "POST") {
      if (!csrfReady) {
        const csrf = await fetch("/api/v1/csrf/", { credentials: "same-origin" });
        if (!csrf.ok || !cookie("csrftoken")) throw new Error("Could not start a secure session. Please try again.");
        csrfReady = true;
      }
      options.headers = { ...options.headers, "X-CSRFToken": cookie("csrftoken") };
    }
    const response = await fetch(url, { credentials: "same-origin", ...options });
    if (!response.ok) {
      let code = "";
      try { code = (await response.json()).error || ""; } catch (_) { /* Django may return HTML. */ }
      const errors = {
        game_not_found: "Game not found. Check the ID and try again.",
        occupied: "That intersection is already occupied. Refresh the game and try another.",
        game_finished: "This game has finished. Refresh to see the result.",
      };
      if (response.status === 403) csrfReady = false;
      throw new Error(errors[code] || "Something went wrong. Please try again.");
    }
    return response.json();
  }

  function nearestAvailable(index) {
    return cells.filter(({ button }) => !button.disabled).sort((a, b) => {
      const distance = (cell) => Math.abs(cell.x - index % 15) + Math.abs(cell.y - Math.floor(index / 15));
      return distance(a) - distance(b);
    })[0];
  }

  function render() {
    const active = game && game.status === "in_progress";
    for (const { button, x, y } of cells) {
      const value = game ? game.board[y][x] : 0;
      button.className = `cell${value === 1 ? " black" : value === 2 ? " white" : ""}`;
      button.disabled = busy || !active || value !== 0;
      button.setAttribute("aria-label", `Row ${y + 1}, column ${x + 1}, ${value === 1 ? "black stone" : value === 2 ? "white stone" : "empty"}`);
    }
    if (!cells[focusedCell] || cells[focusedCell].button.disabled) {
      const available = nearestAvailable(focusedCell);
      if (available) focusedCell = available.y * 15 + available.x;
    }
    for (const cell of cells) cell.button.tabIndex = cell.y * 15 + cell.x === focusedCell ? 0 : -1;
    newButton.disabled = busy;
    loadButton.disabled = busy;
    refreshButton.disabled = busy || !game;
    copyButton.disabled = busy || !game;
    currentId.textContent = game ? game.id : "—";
    const caption = document.getElementById("card-caption");
    const text = document.getElementById("status-text");
    const help = document.getElementById("status-help");
    const stone = document.getElementById("status-stone");
    stone.classList.toggle("white", !!game && (game.winner || game.current_player) === 2);
    const status = (value) => { if (text.textContent !== value) text.textContent = value; };
    if (!game) { caption.textContent = "READY TO PLAY"; status("Start a new game"); help.textContent = "Black plays first. Good luck!"; }
    else if (game.status === "won") { caption.textContent = "GAME OVER"; status(`${game.winner === 1 ? "Black" : "White"} wins!`); help.textContent = "Five in a row. Well played."; }
    else if (game.status === "draw") { caption.textContent = "GAME OVER"; status("It's a draw"); help.textContent = "A full board and a well-matched game."; }
    else { caption.textContent = "CURRENT TURN"; status(`${game.current_player === 1 ? "Black" : "White"} to play`); help.textContent = "Choose an empty intersection."; }
  }

  async function perform(action, restoreBoardFocus = false) {
    if (busy) return;
    busy = true; message.textContent = ""; render();
    try { await action(); } catch (error) { message.textContent = error instanceof Error ? error.message : "Could not connect. Please try again."; }
    finally {
      busy = false; render();
      if (restoreBoardFocus && (!document.activeElement || document.activeElement === document.body)) {
        const available = nearestAvailable(focusedCell);
        if (available) available.button.focus();
        else newButton.focus();
      }
    }
  }

  async function load(id) {
    if (!uuidPattern.test(id)) throw new Error("Enter a valid game ID.");
    const loaded = await request(`/api/v1/games/${id.toLowerCase()}/`);
    game = loaded; remember(game.id); idInput.value = game.id;
  }

  for (let y = 0; y < 15; y++) {
    for (let x = 0; x < 15; x++) {
      const button = document.createElement("button");
      button.type = "button";
      button.addEventListener("focus", () => { focusedCell = y * 15 + x; render(); });
      button.addEventListener("keydown", (event) => {
        const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
        const direction = directions[event.key];
        if (!direction) return;
        event.preventDefault();
        if (direction[0]) {
          for (let index = y * 15 + x + direction[0]; index >= 0 && index < cells.length; index += direction[0]) {
            if (!cells[index].button.disabled) { cells[index].button.focus(); break; }
          }
        } else {
          for (let nextY = y + direction[1]; nextY >= 0 && nextY < 15; nextY += direction[1]) {
            const next = cells[nextY * 15 + x].button;
            if (!next.disabled) { next.focus(); break; }
          }
        }
      });
      button.addEventListener("click", () => {
        const restoreFocus = document.activeElement === button;
        return perform(async () => {
        game = await request(`/api/v1/games/${game.id}/moves/`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ x, y }),
        });
        }, restoreFocus);
      });
      board.appendChild(button); cells.push({ button, x, y });
    }
  }
  newButton.addEventListener("click", () => perform(async () => {
    game = await request("/api/v1/games/", { method: "POST" });
    remember(game.id); idInput.value = game.id;
  }));
  loadButton.addEventListener("click", () => perform(() => load(idInput.value.trim())));
  idInput.addEventListener("keydown", (event) => { if (event.key === "Enter") loadButton.click(); });
  refreshButton.addEventListener("click", () => perform(() => load(game.id)));
  copyButton.addEventListener("click", () => perform(async () => {
    if (!navigator.clipboard) throw new Error("Copy the game ID from the field above.");
    await navigator.clipboard.writeText(game.id); message.textContent = "Game ID copied.";
  }));
  render();
  const saved = remembered();
  if (saved) perform(() => load(saved));
})();
