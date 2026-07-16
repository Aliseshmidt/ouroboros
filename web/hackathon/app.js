(() => {
  "use strict";

  const screens = [
    ["overview", "Обзор"], ["upload", "Цифровой след"], ["trace", "Живая трасса"],
    ["patterns", "Паттерны"], ["hypothesis", "Гипотеза"], ["builder", "Micro-skill"],
    ["sandbox", "Песочница"], ["approval", "Согласование"], ["result", "Результат"],
    ["value", "Эффект"], ["library", "Библиотека"], ["evolution", "Эволюция"],
  ];
  const actionConfig = {
    reset: { path: "/api/reset", next: "overview", label: "Демо возвращено к началу" },
    import: { path: "/api/import", next: "trace", label: "Цифровой след прошёл валидацию" },
    detect_patterns: { path: "/api/action/detect_patterns", next: "patterns", label: "Паттерны рассчитаны" },
    select_hypothesis: { path: "/api/hypothesis/select", next: "builder", label: "Гипотеза зафиксирована" },
    generate_skill: { path: "/api/action/generate_skill", next: "sandbox", label: "Micro-skill собран" },
    run_sandbox: { path: "/api/sandbox/run", next: "approval", label: "Sandbox сохранил rich diff" },
    approve: { path: "/api/approve", next: "result", label: "Выдан одноразовый approval receipt" },
    execute: { path: "/api/action/execute", next: "result", label: "Локальные черновики подготовлены" },
    export_template: { path: "/api/action/export_template", next: "library", label: "Шаблон подготовлен локально" },
    evolve: { path: "/api/action/evolve", next: "evolution", label: "Кандидат v2 проверен" },
    promote: { path: "/api/action/promote", next: "evolution", label: "v2 продвинута в demo stable" },
    rollback: { path: "/api/action/rollback", next: "evolution", label: "Откат к v1 подтверждён" },
  };
  const sampleTrace = { demo: true };

  let currentIndex = 0;
  let selectedPatternId = "pattern-credit-dossier";
  let lastSnapshot = {};

  const byId = (id) => document.getElementById(id);
  const queryAll = (selector) => Array.from(document.querySelectorAll(selector));

  function showScreen(screenId, options = {}) {
    const index = screens.findIndex(([id]) => id === screenId);
    if (index < 0) return;
    currentIndex = index;
    queryAll("[data-screen]").forEach((node) => {
      node.classList.toggle("active", node.dataset.screen === screenId);
    });
    queryAll(".step-link").forEach((node) => {
      const active = node.dataset.screenTarget === screenId;
      node.classList.toggle("active", active);
      if (active) node.setAttribute("aria-current", "step");
      else node.removeAttribute("aria-current");
    });
    byId("screen-counter").textContent = String(index + 1).padStart(2, "0") + " / 12";
    byId("screen-name").textContent = screens[index][1];
    byId("footer-progress-bar").dataset.progress = String(index + 1);
    byId("previous-screen").disabled = index === 0;
    byId("next-screen").disabled = index === screens.length - 1;
    closeMobileMenu();
    if (!options.keepScroll) document.querySelector(".screen-viewport").scrollTo({ top: 0, behavior: "smooth" });
  }

  function showAdjacent(delta) {
    const nextIndex = Math.max(0, Math.min(screens.length - 1, currentIndex + delta));
    showScreen(screens[nextIndex][0]);
  }

  function openMobileMenu() {
    byId("sidebar").classList.add("open");
    byId("mobile-backdrop").classList.add("open");
    byId("mobile-menu").setAttribute("aria-expanded", "true");
  }

  function closeMobileMenu() {
    byId("sidebar").classList.remove("open");
    byId("mobile-backdrop").classList.remove("open");
    byId("mobile-menu").setAttribute("aria-expanded", "false");
  }

  function toast(title, detail, kind = "success") {
    const node = document.createElement("div");
    node.className = "toast " + kind;
    const heading = document.createElement("strong");
    const copy = document.createElement("small");
    heading.textContent = title;
    copy.textContent = detail;
    node.append(heading, copy);
    byId("toast-stack").append(node);
    window.setTimeout(() => node.remove(), 4200);
  }

  function valueAt(object, path) {
    return path.split(".").reduce((value, key) => (
      value && typeof value === "object" && key in value ? value[key] : undefined
    ), object);
  }

  function firstValue(paths) {
    for (const path of paths) {
      const value = valueAt(lastSnapshot, path);
      if (value !== undefined && value !== null) return value;
    }
    return undefined;
  }

  function formatMoney(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? "$" + numeric.toFixed(2) : "$0.00";
  }

  function applySnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return;
    lastSnapshot = snapshot;
    const spent = firstValue([
      "budget.spent_usd", "report.budget.spent_usd", "report.budget.total_spent_usd",
      "report.budget.known_spend_usd",
    ]);
    const budgetNode = document.querySelector('[data-bind="budget.spent_usd"]');
    if (budgetNode && spent !== undefined) budgetNode.textContent = formatMoney(spent);

    const skillHash = firstValue(["skill.hash", "report.skill.hash", "report.skill.sha256"]);
    const hashNode = document.querySelector('[data-bind="skill.hash"]');
    if (hashNode && skillHash) hashNode.textContent = String(skillHash).slice(0, 12);

    const v2Passed = firstValue(["report.sandbox.v2.passed", "sandbox.v2.passed"]);
    const scoreNode = document.querySelector('[data-bind="sandbox.score"]');
    if (scoreNode && v2Passed === true) scoreNode.textContent = "100";

    const executionOk = firstValue(["execution.ok", "report.execution.ok"]);
    if (executionOk === true) {
      const resultTitle = byId("result-title");
      const resultState = byId("result-state");
      if (resultTitle) resultTitle.textContent = "Мини-досье готово к проверке";
      if (resultState) resultState.textContent = "Исполнено · audit-backed";
    }

    const patterns = firstValue(["patterns", "report.patterns"]);
    if (Array.isArray(patterns) && patterns.length) {
      const cards = queryAll(".pattern-card");
      cards.forEach((card, index) => {
        if (patterns[index] && patterns[index].pattern_id) {
          card.dataset.backendPatternId = patterns[index].pattern_id;
        }
      });
      const selectedCard = document.querySelector(".pattern-card.selected") || cards[0];
      selectedPatternId = selectedCard.dataset.backendPatternId || patterns[0].pattern_id;
    }
  }

  function actionBody(action, button) {
    if (action === "import") return { payload: sampleTrace, format: "json" };
    if (action === "select_hypothesis") return { pattern_id: selectedPatternId };
    if (action === "run_sandbox") return { version: button.dataset.version || "1.0.0" };
    if (action === "approve") return { action: "execute" };
    return {};
  }

  async function postJson(path, body) {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let payload;
    try {
      payload = await response.json();
    } catch (_error) {
      throw new Error("HTTP " + response.status + ": некорректный ответ сервера");
    }
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || "HTTP " + response.status);
    }
    return payload;
  }

  async function runAction(button) {
    const action = button.dataset.action;
    const config = actionConfig[action];
    if (!config) return;
    const originalText = button.textContent;
    button.disabled = true;
    button.classList.add("working");
    button.textContent = "Выполняется…";
    try {
      const payload = await postJson(config.path, actionBody(action, button));
      applySnapshot(payload.snapshot || {});
      toast(config.label, "Локальная детерминированная операция завершена.");
      showScreen(config.next);
    } catch (error) {
      toast("Операция не выполнена", error.message, "error");
    } finally {
      button.disabled = false;
      button.classList.remove("working");
      button.textContent = originalText;
    }
  }

  function selectPattern(patternId) {
    const selectedCard = document.querySelector('[data-pattern-id="' + patternId + '"]');
    selectedPatternId = selectedCard && selectedCard.dataset.backendPatternId
      ? selectedCard.dataset.backendPatternId
      : patternId;
    queryAll(".pattern-card").forEach((card) => {
      const selected = card.dataset.patternId === patternId;
      card.classList.toggle("selected", selected);
      const button = card.querySelector("[data-select-pattern]");
      if (button) button.textContent = selected ? "Выбрано ✓" : "Выбрать";
    });
    toast("Паттерн выбран", "Гипотеза будет связана с измеренным источником.");
  }

  async function checkBackend() {
    const note = byId("connection-note");
    try {
      const response = await fetch("/api/state", { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) throw new Error(payload.error || "backend unavailable");
      applySnapshot(payload.snapshot || {});
      note.textContent = "● Backend подключён · deterministic local demo";
      note.classList.add("connected");
    } catch (error) {
      note.textContent = "● Preview UI · backend недоступен";
      note.classList.add("unavailable");
      note.title = error.message;
    }
  }

  document.addEventListener("click", (event) => {
    const screenButton = event.target.closest("[data-screen-target]");
    if (screenButton) {
      showScreen(screenButton.dataset.screenTarget);
      return;
    }
    const patternButton = event.target.closest("[data-select-pattern]");
    if (patternButton) {
      selectPattern(patternButton.dataset.selectPattern);
      return;
    }
    const actionButton = event.target.closest("[data-action]");
    if (actionButton) runAction(actionButton);
  });

  byId("previous-screen").addEventListener("click", () => showAdjacent(-1));
  byId("next-screen").addEventListener("click", () => showAdjacent(1));
  byId("mobile-menu").addEventListener("click", () => {
    if (byId("sidebar").classList.contains("open")) closeMobileMenu();
    else openMobileMenu();
  });
  byId("mobile-backdrop").addEventListener("click", closeMobileMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMobileMenu();
    if (event.altKey && event.key === "ArrowRight") showAdjacent(1);
    if (event.altKey && event.key === "ArrowLeft") showAdjacent(-1);
  });

  showScreen("overview", { keepScroll: true });
  checkBackend();
})();
