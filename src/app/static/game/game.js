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
  const modeSelect = document.getElementById("game-mode");
  const enableForbiddenMoves = document.getElementById("enable-forbidden-moves");
  const forbiddenOptions = document.getElementById("forbidden-options");
  const forbiddenConsequence = document.getElementById("forbidden-consequence");
  const activePolicy = document.getElementById("active-policy");
  const retryButton = document.getElementById("retry-turn");
  const resultDetails = document.getElementById("result-details");
  const forbiddenDialog = document.getElementById("forbidden-dialog");
  const forbiddenTitle = document.getElementById("forbidden-title");
  const forbiddenExplanation = document.getElementById("forbidden-explanation");
  const forbiddenNext = document.getElementById("forbidden-next");
  const forbiddenDismiss = document.getElementById("forbidden-dismiss");
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  let game = null;
  let busy = false;
  let syncRequired = false;
  let csrfReady = false;
  const cells = [];
  let focusedCell = 0;
  const policyLabels = { off: "Off", warn: "Warn and retry", loss: "Immediate loss" };
  const forbiddenReasons = {
    overline: "Overline. Black forms a row of six or more stones.",
    double_four: "Double-four. Black forms more than one four.",
    double_three: "Double-three. Black forms more than one open three.",
  };

  class GameRequestError extends Error {
    constructor(message, code, status, reason) {
      super(message);
      this.code = code;
      this.status = status;
      this.reason = reason;
    }
  }

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
      let error = {};
      try { error = (await response.json()) || {}; } catch (_) { /* Django may return HTML. */ }
      const code = error.error;
      const errors = {
        game_not_found: "Game not found. Check the ID and try again.",
        occupied: "That intersection is already occupied. Refresh the game and try another.",
        game_finished: "This game has finished. Refresh to see the result.",
        not_human_turn: "The game is waiting for the CPU.",
        stale_revision: "The game has moved on. Check the updated board.",
        cpu_creation_unavailable: "New CPU games are temporarily unavailable.",
        invalid_forbidden_move_policy: "Choose a supported forbidden-move setting.",
      };
      if (response.status === 403) csrfReady = false;
      throw new GameRequestError(
        errors[code] || "Something went wrong. Please try again.",
        code,
        response.status,
        error.reason,
      );
    }
    return response.json();
  }

  function nearestAvailable(index) {
    return cells.filter(({ button }) => !button.disabled).sort((a, b) => {
      const distance = (cell) => Math.abs(cell.x - index % 15) + Math.abs(cell.y - Math.floor(index / 15));
      return distance(a) - distance(b);
    })[0];
  }

  function cpuPending() {
    return game?.mode === "cpu" && game.status === "in_progress" && game.current_player === 2;
  }

  function showForbiddenNotice(reason, loss = false) {
    forbiddenTitle.textContent = loss ? "White wins by forbidden move" : "Forbidden move";
    forbiddenExplanation.textContent = forbiddenReasons[reason] || "This move is forbidden for black.";
    forbiddenNext.textContent = loss ? "" : "Black keeps the turn.";
    forbiddenNext.hidden = loss;
    forbiddenDismiss.textContent = loss ? "Back to board" : "Choose another move";
    forbiddenDialog.showModal();
  }

  function render() {
    const active = game && game.status === "in_progress";
    const cpu = game?.mode === "cpu";
    const pending = cpuPending();
    board.dataset.currentPlayer = active ? String(game.current_player) : "";
    for (const { button, x, y } of cells) {
      const value = game ? game.board[y][x] : 0;
      button.className = `cell${value === 1 ? " black" : value === 2 ? " white" : ""}`;
      button.disabled = busy || !active || pending || syncRequired || value !== 0;
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
    modeSelect.disabled = busy;
    enableForbiddenMoves.disabled = busy;
    forbiddenOptions.hidden = !enableForbiddenMoves.checked;
    forbiddenConsequence.disabled = busy || forbiddenOptions.hidden;
    activePolicy.hidden = !game;
    activePolicy.textContent = game ? `Black forbidden moves: ${policyLabels[game.forbidden_move_policy ?? "off"]}` : "";
    resultDetails.hidden = !Object.hasOwn(forbiddenReasons, game?.result_reason);
    resultDetails.disabled = busy;
    retryButton.hidden = !syncRequired && !pending;
    retryButton.disabled = busy || retryButton.hidden;
    retryButton.textContent = syncRequired ? "Reload saved game" : "Retry CPU turn";
    currentId.textContent = game ? game.id : "—";
    const caption = document.getElementById("card-caption");
    const text = document.getElementById("status-text");
    const help = document.getElementById("status-help");
    const stone = document.getElementById("status-stone");
    stone.classList.toggle("white", !!game && (game.winner || game.current_player) === 2);
    const status = (value) => { if (text.textContent !== value) text.textContent = value; };
    if (!game) { caption.textContent = "READY TO PLAY"; status("Start a new game"); help.textContent = "Black plays first. Good luck!"; }
    else if (game.status === "won") {
      caption.textContent = "GAME OVER";
      const result = cpu ? (game.winner === 1 ? "You win!" : "CPU wins!") : `${game.winner === 1 ? "Black" : "White"} wins!`;
      if (game.result_reason === "no_legal_black_move") {
        status(`${result} Black has no legal move.`);
        help.textContent = "";
      } else if (forbiddenReasons[game.result_reason]) {
        status(result);
        help.textContent = "";
      } else {
        status(result);
        help.textContent = cpu ? "CPU game · You played black." : "Five in a row. Well played.";
      }
    }
    else if (game.status === "draw") { caption.textContent = "GAME OVER"; status("It's a draw"); help.textContent = cpu ? "CPU game · You played black." : "A full board and a well-matched game."; }
    else if (cpu) {
      caption.textContent = "CPU GAME";
      status(syncRequired ? "Checking the saved turn" : pending ? "CPU to play (white)" : "Your turn (black)");
      help.textContent = pending || syncRequired ? "You play black." : "Choose an empty intersection.";
    } else {
      caption.textContent = "TWO PLAYERS";
      status(`${game.current_player === 1 ? "Black" : "White"} to play`);
      help.textContent = "Choose an empty intersection.";
    }
  }

  async function perform(action, restoreBoardFocus = false) {
    if (busy) return;
    const previousGame = game;
    let warning;
    busy = true; message.textContent = ""; render();
    try {
      await action();
    } catch (error) {
      if (error instanceof GameRequestError && error.code === "forbidden_move") warning = error;
      else message.textContent = error instanceof Error ? error.message : "Could not connect. Please try again.";
    }
    finally {
      busy = false; render();
      if (warning) {
        showForbiddenNotice(warning.reason);
      } else if (game !== previousGame && !resultDetails.hidden) {
        showForbiddenNotice(game.result_reason, true);
      } else if (restoreBoardFocus && (!document.activeElement || document.activeElement === document.body)) {
        const available = nearestAvailable(focusedCell);
        if (available) available.button.focus();
        else if (!retryButton.hidden) retryButton.focus();
        else newButton.focus();
      }
    }
  }

  function setGame(saved) {
    game = saved;
    syncRequired = false;
    remember(game.id);
    idInput.value = game.id;
  }

  async function readGame(id) {
    if (!uuidPattern.test(id)) throw new Error("Enter a valid game ID.");
    setGame(await request(`/api/v1/games/${id.toLowerCase()}/`));
  }

  function postJson(url, payload) {
    return request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async function advanceCpu() {
    while (cpuPending()) {
      render();
      // Let the confirmed human stone and white turn paint before the POST.
      if (typeof requestAnimationFrame === "function" && !document.hidden) {
        await new Promise((resolve) => {
          const fallback = setTimeout(resolve, 100);
          requestAnimationFrame(() => requestAnimationFrame(() => {
            clearTimeout(fallback);
            resolve();
          }));
        });
      }
      const revision = game.revision;
      try {
        game = await postJson(`/api/v1/games/${game.id}/cpu-move/`, { expected_revision: revision });
      } catch {
        throw new Error("The CPU turn was interrupted. Retry to check the saved board and continue.");
      }
      if (cpuPending() && game.revision <= revision) {
        throw new Error("The CPU turn did not advance. Retry to check the saved board.");
      }
    }
  }

  async function load(id) {
    await readGame(id);
    await advanceCpu();
  }

  async function placeMove(x, y) {
    const { id, mode, revision } = game;
    const payload = mode === "cpu" ? { x, y, expected_revision: revision } : { x, y };
    try {
      game = await postJson(`/api/v1/games/${id}/moves/`, payload);
    } catch (error) {
      if (error instanceof GameRequestError) {
        if (error.code === "forbidden_move" || (mode !== "cpu" && error.status < 500)) throw error;
      }
      syncRequired = true;
      try {
        await readGame(id);
      } catch {
        throw new Error("Could not confirm your move. Reload the saved game before playing again.");
      }
      if (game.revision === revision) throw error;
    }
    await advanceCpu();
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
        if (button.disabled || busy || !game || cpuPending() || syncRequired) return;
        const restoreFocus = document.activeElement === button;
        return perform(() => placeMove(x, y), restoreFocus);
      });
      board.appendChild(button); cells.push({ button, x, y });
    }
  }
  enableForbiddenMoves.addEventListener("change", render);
  newButton.addEventListener("click", () => perform(async () => {
    const created = await postJson("/api/v1/games/", {
      mode: modeSelect.value,
      forbidden_move_policy: enableForbiddenMoves.checked ? forbiddenConsequence.value : "off",
    });
    setGame(created);
  }));
  loadButton.addEventListener("click", () => perform(() => load(idInput.value.trim())));
  idInput.addEventListener("keydown", (event) => { if (event.key === "Enter") loadButton.click(); });
  refreshButton.addEventListener("click", () => perform(() => load(game.id)));
  retryButton.addEventListener("click", () => perform(() => load(game.id), true));
  resultDetails.addEventListener("click", () => showForbiddenNotice(game.result_reason, true));
  forbiddenDialog.addEventListener("close", () => {
    if (resultDetails.hidden) nearestAvailable(focusedCell)?.button.focus();
    else resultDetails.focus();
  });
  copyButton.addEventListener("click", () => perform(async () => {
    try {
      await navigator.clipboard.writeText(game.id);
      message.textContent = "Game ID copied.";
    } catch {
      message.textContent = "Copy the game ID shown below the board.";
    }
  }));
  render();
  const saved = remembered();
  if (saved) perform(() => load(saved));
})();
