/* ------------------------------------------------------------------
   Frontend.

   Plain JavaScript on purpose — no React, no build step, no npm. Open
   index.html, hit refresh, see the change. Once this makes sense you
   can port it to a framework, but you'll understand what the framework
   is doing for you.

   The whole app is a small state machine:

       intro  ->  question 0..5  ->  results
                       ^                |
                       +-- start over --+

   Everything the user has picked lives in `state`. Rendering is a pure
   function of that object: change the state, call render(), done.
   ------------------------------------------------------------------ */

const state = {
  lang: "en",
  questions: [],   // fetched from the server
  ui: {},          // button labels etc., also from the server
  screen: "intro", // "intro" | "question" | "results"
  step: 0,         // which question we're on
  answers: {},     // { questionId: [optionId, ...] }
  games: [],       // recommendations collected so far
  offset: 0,       // how many we've already been given
  hasMore: false,
  total: 0,
  busy: false,
  warning: null,
};

const stage = document.getElementById("stage");

/* --- Talking to the server ---------------------------------------
   Two calls, that's the entire API surface. `fetch` returns a Promise,
   so we use async/await to read it as if it were ordinary code. */

async function loadQuestions(lang) {
  const response = await fetch(`/api/questions?lang=${lang}`);
  if (!response.ok) throw new Error(`Server said ${response.status}`);
  return response.json();
}

async function loadRecommendations(offset) {
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answers: state.answers,
      offset: offset,
      lang: state.lang,
    }),
  });
  if (!response.ok) throw new Error(`Server said ${response.status}`);
  return response.json();
}

/* --- Small helpers ------------------------------------------------ */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function currentQuestion() {
  return state.questions[state.step];
}

function picked(questionId) {
  return state.answers[questionId] || [];
}

/* --- Actions ------------------------------------------------------
   Each of these changes state, then re-renders. Never touch the DOM
   directly from an event handler; go through the state. */

function choose(questionId, optionId, type) {
  state.warning = null;

  if (type === "single") {
    state.answers[questionId] = [optionId];
    // Single-choice questions advance on their own — one tap, not two.
    if (state.step < state.questions.length - 1) {
      state.step += 1;
      render();
    } else {
      finish();
    }
    return;
  }

  // Multi-choice: toggle the option and wait for the Next button.
  const chosen = new Set(picked(questionId));
  chosen.has(optionId) ? chosen.delete(optionId) : chosen.add(optionId);
  state.answers[questionId] = [...chosen];
  render();
}

function goNext() {
  const question = currentQuestion();
  if (question.required && picked(question.id).length === 0) {
    state.warning = state.ui.select_one;
    render();
    return;
  }
  state.warning = null;
  if (state.step < state.questions.length - 1) {
    state.step += 1;
    render();
  } else {
    finish();
  }
}

function goBack() {
  state.warning = null;
  if (state.step === 0) {
    state.screen = "intro";
  } else {
    state.step -= 1;
  }
  render();
}

async function finish() {
  state.screen = "results";
  state.games = [];
  state.offset = 0;
  await fetchMore();
}

/* This is the "show 3 more" button. It asks for the same ranked list
   starting further down, then appends. Because the server's ranking is
   deterministic, page two never repeats page one. */
async function fetchMore() {
  state.busy = true;
  render();
  try {
    const data = await loadRecommendations(state.offset);
    state.games = state.games.concat(data.games);
    state.offset += data.games.length;
    state.hasMore = data.has_more;
    state.total = data.total;
    state.warning = null;
  } catch (error) {
    console.error(error);
    state.warning = state.ui.error;
  } finally {
    state.busy = false;
    render();
  }
}

function restart() {
  state.screen = "intro";
  state.step = 0;
  state.answers = {};
  state.games = [];
  state.offset = 0;
  state.warning = null;
  render();
}

async function switchLanguage(lang) {
  if (lang === state.lang) return;
  state.lang = lang;
  document.documentElement.lang = lang;
  document.querySelectorAll(".langbtn").forEach((button) => {
    button.classList.toggle("is-on", button.dataset.lang === lang);
  });

  const data = await loadQuestions(lang);
  state.questions = data.questions;
  state.ui = data.ui;
  document.getElementById("wordmark").textContent = state.ui.title;
  document.title = state.ui.title;

  // Answers survive a language change — the option ids don't change,
  // only their labels. If we're already looking at results, refresh them
  // so the explanations come back translated.
  if (state.screen === "results") {
    state.games = [];
    state.offset = 0;
    await fetchMore();
  } else {
    render();
  }
}

/* --- Screens ------------------------------------------------------ */

function renderIntro() {
  const title = el("h1", "intro-title", state.ui.title);
  const sub = el("p", "intro-sub", state.ui.subtitle);

  const start = el("button", "btn btn-go", state.ui.start);
  start.addEventListener("click", () => {
    state.screen = "question";
    state.step = 0;
    render();
  });

  const row = el("div", "row");
  row.append(start);
  stage.append(title, sub, row);
}

function renderQuestion() {
  const question = currentQuestion();

  const progress = el("div", "progress");
  state.questions.forEach((_, index) => {
    const bar = el("span", index <= state.step ? "done" : "");
    progress.append(bar);
  });

  const title = el("h1", "q-title", question.text);
  stage.append(progress, title);

  if (question.hint) stage.append(el("p", "q-hint", question.hint));

  const list = el("ul", "options");
  question.options.forEach((option) => {
    const item = el("li");
    const button = el("button", "opt", option.label);
    button.type = "button";
    if (picked(question.id).includes(option.id)) {
      button.classList.add("is-picked");
      button.setAttribute("aria-pressed", "true");
    } else {
      button.setAttribute("aria-pressed", "false");
    }
    button.addEventListener("click", () =>
      choose(question.id, option.id, question.type)
    );
    item.append(button);
    list.append(item);
  });
  stage.append(list);

  const row = el("div", "row");
  const isLast = state.step === state.questions.length - 1;

  // Single-choice questions advance on tap, so they don't need a Next
  // button. Multi-choice ones do, because we can't know when the user
  // is finished picking.
  if (question.type === "multi") {
    const next = el("button", "btn btn-go", isLast ? state.ui.finish : state.ui.next);
    next.addEventListener("click", goNext);
    row.append(next);
  } else if (!question.required) {
    const skip = el("button", "btn btn-quiet", state.ui.next);
    skip.addEventListener("click", goNext);
    row.append(skip);
  }

  const back = el("button", "btn btn-quiet", state.ui.back);
  back.addEventListener("click", goBack);
  row.append(back);

  stage.append(row);

  if (state.warning) stage.append(el("p", "warn", state.warning));
}

function renderGame(game) {
  const card = el("article", "game");

  if (game.image) {
    const cover = el("img", "cover");
    cover.src = game.image;
    cover.alt = "";
    cover.loading = "lazy";
    card.append(cover);
  }

  const figure = el("div", "figure", `${game.match_percent}`);
  figure.append(el("small", null, state.ui.match));
  card.append(figure);

  const body = el("div");

  const name = el("h3", "game-name");
  if (game.url) {
    const link = el("a", null, game.name);
    link.href = game.url;
    link.target = "_blank";
    link.rel = "noopener";
    name.append(link);
  } else {
    name.textContent = game.name;
  }
  body.append(name);

  // Build the meta line from whatever we actually have, so a game with
  // no critic score doesn't render an empty gap or a stray separator.
  const bits = [];
  if (game.year) bits.push(game.year);
  if (game.metacritic) bits.push(`${state.ui.score} ${game.metacritic}`);
  if (game.playtime) bits.push(`~${game.playtime} ${state.ui.hours}`);
  if (game.genres.length) bits.push(game.genres.slice(0, 2).join(", "));
  body.append(el("p", "game-meta", bits.join(" · ")));

  if (game.reasons.length) {
    const chips = el("div", "chips");
    game.reasons.forEach((reason) => chips.append(el("span", "chip", reason)));
    body.append(chips);
  }

  card.append(body);
  return card;
}

function renderResults() {
  const head = el("div", "results-head");
  head.append(el("h2", null, state.ui.title));
  if (state.total) {
    head.append(
      el("span", "count", `${state.games.length} ${state.ui.of} ${state.total}`)
    );
  }
  stage.append(head);

  if (state.games.length === 0 && !state.busy) {
    stage.append(el("p", "status", state.warning || state.ui.empty));
  }

  state.games.forEach((game) => stage.append(renderGame(game)));

  if (state.busy) stage.append(el("p", "status", state.ui.loading));

  const foot = el("div", "results-foot");
  const row = el("div", "row");

  if (state.hasMore) {
    const more = el("button", "btn btn-go", state.ui.more);
    more.disabled = state.busy;
    more.addEventListener("click", fetchMore);
    row.append(more);
  }

  const again = el("button", "btn btn-quiet", state.ui.restart);
  again.addEventListener("click", restart);
  row.append(again);

  foot.append(row);
  stage.append(foot);

  if (state.warning && state.games.length) stage.append(el("p", "warn", state.warning));
}

function render() {
  stage.replaceChildren();
  if (state.screen === "intro") renderIntro();
  else if (state.screen === "question") renderQuestion();
  else renderResults();
}

/* --- Boot --------------------------------------------------------- */

document.querySelectorAll(".langbtn").forEach((button) => {
  button.addEventListener("click", () => switchLanguage(button.dataset.lang));
});

(async function start() {
  try {
    const data = await loadQuestions(state.lang);
    state.questions = data.questions;
    state.ui = data.ui;
    document.getElementById("wordmark").textContent = state.ui.title;
    document.title = state.ui.title;
    render();
  } catch (error) {
    console.error(error);
    stage.replaceChildren(
      el("p", "status", "Couldn't reach the server. Is uvicorn running?")
    );
  }
})();
