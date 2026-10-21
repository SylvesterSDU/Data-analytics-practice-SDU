// Data Analytics in Accounting practice site.
// Improvement over the reference site: "Check my result" for Excel/SQL tasks + verified topic mastery.
// Expected values exist only as SHA-256 hashes (see tools/build_questions.py).

const STORE_KEY = "dap-progress-v1";
const STREAK_TARGET = 3;
const D = { salt: "", topics: [], bank: [], byId: {}, exams: [], reg: [] };

// ---------- progress (this browser only) ----------
function loadProgress() {
  try {
    const p = JSON.parse(localStorage.getItem(STORE_KEY));
    if (p && p.verified && p.topics) return p;
  } catch (e) { /* storage blocked or corrupt */ }
  return { verified: {}, topics: {} };
}
let progress = loadProgress();
function saveProgress() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(progress)); } catch (e) { /* ignore */ }
}
function topicState(topic) {
  if (!progress.topics[topic]) progress.topics[topic] = { run: [], fresh: 0, mastered: false };
  return progress.topics[topic];
}
// A run only earns the check mark if it contains at least one question the student had not
// solved before, so a student cannot rebuild a run by retyping remembered figures.
// Waived when every question in the topic has already been verified.
function needsFresh(topic, st) {
  if ((st.fresh || 0) > 0) return false;
  return D.bank.some(x => x.topic === topic && !progress.verified[x.id]);
}

// ---------- hashing ----------
async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
const hashFor = (qid, idx, canon) => sha256(`${D.salt}|${qid}|${idx}|${canon}`);

// ---------- input normalisation ----------
// Numbers: 1234.5, 1,234.50, 1.234,50 (Danish), 1 234,5, $1,234.50, (1,234.50) for negatives.
function numberCandidates(raw) {
  let s = String(raw).trim().replace(/[\s ]/g, "").replace(/^(\$|kr\.?|dkk)/i, "").replace(/(kr\.?|dkk)$/i, "");
  let neg = false;
  if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
  if (s.startsWith("-") || s.startsWith("−")) { neg = !neg; s = s.slice(1); }
  s = s.replace(/^\$/, "").replace(/%$/, "");
  if (!/^[\d.,]+$/.test(s) || !/\d/.test(s)) return [];

  const out = new Set();
  const dots = (s.match(/\./g) || []).length;
  const commas = (s.match(/,/g) || []).length;
  if (dots && commas) {
    const dec = s.lastIndexOf(".") > s.lastIndexOf(",") ? "." : ",";
    const thou = dec === "." ? "," : ".";
    out.add(s.split(thou).join("").replace(dec, "."));
  } else if (dots + commas === 0) {
    out.add(s);
  } else {
    const sep = dots ? "." : ",";
    if ((dots || commas) > 1) {
      out.add(s.split(sep).join(""));                    // only thousands separators
    } else {
      out.add(s.replace(sep, "."));                     // decimal separator
      if (/^\d{1,3}[.,]\d{3}$/.test(s)) out.add(s.replace(sep, "")); // or a thousands separator
    }
  }
  return [...out].map(Number).filter(Number.isFinite).map(n => (neg ? -n : n));
}

function canonNumbers(n, decimals) {
  const f = 10 ** decimals;
  const base = [n];
  if (decimals > 0) base.push(n + 1 / f, n - 1 / f); // tolerate rounding in the last decimal
  return base.map(v => (Math.round(v * f) / f + 0).toFixed(decimals));
}
const canonText = s => String(s).trim().toLowerCase().split(/\s+/).join(" ");

// Dates: 2011-12-07 16:38, 12/7/2011 16:38, 7-12-2011 4:38 PM. Day/month order is ambiguous, so both are tried.
function dateCandidates(raw, withTime) {
  const s = String(raw).trim();
  const pad = n => String(n).padStart(2, "0");
  const parts = [];
  let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(.*)$/);
  if (m) parts.push([+m[1], +m[2], +m[3], m[4]]);
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(.*)$/);
  if (m) parts.push([+m[3], +m[1], +m[2], m[4]], [+m[3], +m[2], +m[1], m[4]]);
  const out = [];
  for (const [y, mo, d, rest] of parts) {
    if (mo < 1 || mo > 12 || d < 1 || d > 31) continue;
    let iso = `${y}-${pad(mo)}-${pad(d)}`;
    if (withTime) {
      const t = rest.match(/(\d{1,2})[:.](\d{2})(?:[:.]\d{2})?\s*(am|pm)?/i);
      if (!t) continue;
      let h = +t[1];
      if (t[3] && /pm/i.test(t[3]) && h < 12) h += 12;
      if (t[3] && /am/i.test(t[3]) && h === 12) h = 0;
      iso += ` ${pad(h)}:${t[2]}`;
    }
    out.push(iso);
  }
  return out;
}

async function evaluate(q, idx, raw) {
  const check = q.checks[idx];
  let canons;
  if (check.type === "number") {
    let nums = numberCandidates(raw);
    if (!nums.length) return { state: "bad", msg: "Type a number, e.g. 1234.56 or 1.234,56." };
    if (check.percent && !String(raw).includes("%")) nums = nums.concat(nums.map(n => n * 100)); // 0.0784 or 7.84
    canons = nums.flatMap(n => canonNumbers(n, check.decimals));
  } else if (check.type === "date") {
    canons = dateCandidates(raw, check.time);
    if (!canons.length) {
      return { state: "bad", msg: check.time ? "Type a date and time, e.g. 2011-12-07 16:38." : "Type a date, e.g. 2009-01-01." };
    }
  } else {
    canons = [canonText(raw)];
  }
  const hashes = await Promise.all([...new Set(canons)].map(c => hashFor(q.id, idx, c)));
  if (hashes.includes(check.hash) || (check.accept || []).some(h => hashes.includes(h))) return { state: "ok", msg: "Matches." };
  for (const m of check.mistakes || []) {
    if (hashes.includes(m.hash)) return { state: "hint", msg: m.hint };
  }
  const extra = check.type === "number" && check.decimals > 0 ? ` (checked to ${check.decimals} decimals)` : "";
  return { state: "bad", msg: `Does not match${extra}. Re-check your filters and the column you aggregate.` };
}

// ---------- small helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) n.append(k.nodeType ? k : String(k));
  return n;
}
const sources = () => [...new Set(D.bank.map(q => q.source))];

// ---------- topic mastery panel ----------
function renderTopics() {
  const ul = $("#topics");
  ul.innerHTML = "";
  let mastered = 0;
  for (const t of D.topics) {
    const st = topicState(t);
    const qs = D.bank.filter(q => q.topic === t);
    const verified = qs.filter(q => progress.verified[q.id]).length;
    if (st.mastered) mastered++;
    const right = st.mastered
      ? el("span", { class: "badge" }, "✓ Mastered")
      : el("span", { class: "dots", title: `${st.run.length} of ${STREAK_TARGET} in a row` },
          ...Array.from({ length: STREAK_TARGET }, (_, i) => el("span", { class: `dot${i < st.run.length ? " on" : ""}` })));
    const btn = el("button", { class: "topic-btn", type: "button", onclick: () => { filters.topic = t; location.hash = "#/bank"; render(); } },
      el("span", { class: "topic-name" }, t),
      el("span", { class: "topic-sub" }, !st.mastered && st.run.length >= STREAK_TARGET && needsFresh(t, st)
        ? "3 in a row: now solve one new question" : `${verified} of ${qs.length} verified`));
    ul.append(el("li", {}, btn, right));
  }
  $("#overall").textContent = `${mastered} of ${D.topics.length} topics mastered`;
}

// ---------- question card ----------
function questionCard(q, onChange) {
  const node = $("#q-tpl").content.firstElementChild.cloneNode(true);
  node.dataset.qid = q.id;
  const meta = $(".meta", node);
  for (const [cls, text] of [["subject", q.subject], ["", q.source], ["", q.topic], ["", `~${q.minutes} min`], ["id", q.id]]) {
    meta.append(el("span", { class: `tag ${cls}` }, text));
  }
  $(".prompt", node).textContent = q.prompt;
  if (q.note) $(".prompt", node).after(el("p", { class: "note" }, q.note));
  const dl = $(".downloads", node);
  for (const f of q.files) dl.append(el("a", { href: `files/${f}`, download: "" }, f));
  const fields = $(".fields", node);
  q.checks.forEach((c, i) => {
    const id = `${q.id}-${i}`;
    fields.append(el("div", { class: "field" },
      el("label", { for: id }, c.label),
      el("input", { id, autocomplete: "off", inputmode: c.type === "number" ? "decimal" : "text" }),
      el("div", { class: "feedback" })));
  });
  $("form", node).addEventListener("submit", e => { e.preventDefault(); onCheck(q, node).then(() => onChange && onChange()); });
  node.append(tutorPanel(q, node));
  markVerified(q, node);
  return node;
}

// ---------- AI tutor (result-aware) ----------
// The tutor gets the task, the real dataset description and the latest check result
// (which figures matched, which known mistake was hit). It never gets the answers: the site only has hashes.
function renderReply(text) {
  const box = el("div", { class: "msg-body" });
  text.split(/```(?:\w+)?\n?/).forEach((chunk, i) => {
    if (i % 2) { box.append(el("pre", {}, el("code", {}, chunk.trim()))); return; }
    chunk.split(/\n{2,}/).filter(p => p.trim()).forEach(p => {
      const para = el("p");
      p.split(/(`[^`]+`)/).forEach(part => {
        if (/^`[^`]+`$/.test(part)) para.append(el("code", {}, part.slice(1, -1)));
        // Drop markdown emphasis (*word*, **word**) but keep things like COUNT(*).
        else para.append(part.replace(/(^|[\s(])\*{1,2}([A-Za-z][^*\n]*?)\*{1,2}(?=[\s.,;:!?)]|$)/g, "$1$2"));
      });
      box.append(para);
    });
  });
  return box;
}

function tutorPanel(q, card) {
  const history = [];
  const log = el("div", { class: "tutor-log", "aria-live": "polite" });
  const seen = el("p", { class: "muted small tutor-seen" });
  const input = el("textarea", { rows: 3, placeholder: "Paste your formula or query and what you got, or ask what to try next." });
  const send = el("button", { type: "submit", class: "btn" }, "Ask tutor");
  const err = el("p", { class: "tutor-err small", role: "status" });
  const describeSeen = () => {
    const r = card._lastCheck;
    seen.textContent = !r ? "The tutor will see your latest check result. Check your figures first for the most specific help."
      : `The tutor sees your latest check: ${r.filter(x => x.state === "ok").length} of ${r.length} figures match.`;
  };
  card._onChecked = describeSeen;
  describeSeen();
  const form = el("form", { class: "tutor-form", onsubmit: async e => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message || send.disabled) return;
    err.textContent = "";
    send.disabled = true;
    send.textContent = "Thinking…";
    log.append(el("div", { class: "msg user" }, el("div", { class: "msg-body" }, el("p", {}, message))));
    const checks = q.checks.map((c, i) => {
      const r = card._lastCheck && card._lastCheck[i];
      return { label: c.label, state: r ? r.state : "none", value: r ? r.value : "", hint: r && r.state === "hint" ? r.msg : "" };
    });
    try {
      const resp = await fetch("api/tutor", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: q.subject, source: q.source, topic: q.topic, prompt: q.prompt, note: q.note || "",
          datasets: q.files.map(f => `${f}:\n${D.schemas[f] || ""}`).join("\n\n"), checks, message, history }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.reply) throw new Error(data.error || `The tutor is not available right now (${resp.status}).`);
      history.push({ role: "user", text: message }, { role: "model", text: data.reply });
      log.append(el("div", { class: "msg tutor" }, renderReply(data.reply)));
      input.value = "";
    } catch (ex) {
      log.lastElementChild.remove();
      err.textContent = ex.message || "The tutor is not available right now.";
    } finally {
      send.disabled = false;
      send.textContent = "Ask tutor";
    }
  } }, input, el("div", { class: "actions" }, send, err));
  return el("details", { class: "tutor" },
    el("summary", {}, "Ask the AI tutor"),
    el("p", { class: "muted small" }, "Hints only, never the answer. The tutor does not know the correct figures either; it only knows whether yours match."),
    seen, log, form);
}

function markVerified(q, node) {
  if (!progress.verified[q.id] || $(".tag.verified", node)) return;
  node.classList.add("done");
  $(".meta", node).append(el("span", { class: "tag verified" }, "✓ Verified"));
}

async function onCheck(q, node) {
  const fieldEls = [...node.querySelectorAll(".field")];
  const status = $(".status", node);
  const values = fieldEls.map(f => $("input", f).value);
  if (values.some(v => !v.trim())) {
    status.className = "status bad";
    status.textContent = "Fill in every box before checking.";
    return;
  }
  const results = await Promise.all(values.map((v, i) => evaluate(q, i, v)));
  results.forEach((r, i) => {
    const f = fieldEls[i];
    f.classList.remove("ok", "bad");
    f.classList.add(r.state === "ok" ? "ok" : "bad");
    const fb = $(".feedback", f);
    fb.className = `feedback ${r.state}`;
    fb.textContent = r.msg;
  });
  node._lastCheck = results.map((r, i) => ({ ...r, value: values[i] }));
  if (node._onChecked) node._onChecked();

  const st = topicState(q.topic);
  if (results.every(r => r.state === "ok")) {
    const wasNew = !progress.verified[q.id];
    progress.verified[q.id] = new Date().toISOString();
    if (!st.run.includes(q.id)) {
      st.run.push(q.id);
      if (wasNew) st.fresh = (st.fresh || 0) + 1;
    }
    const waiting = needsFresh(q.topic, st);
    const justMastered = !st.mastered && st.run.length >= STREAK_TARGET && !waiting;
    if (justMastered) st.mastered = true;
    status.className = "status ok";
    status.textContent = justMastered ? `All correct. ${q.topic}: mastered!`
      : st.mastered ? "All correct."
      : st.run.length >= STREAK_TARGET ? `All correct. ${st.run.length} in a row, but you had solved all of them before. Verify one question in this topic you haven't solved yet to earn the check mark.`
      : `All correct. ${st.run.length} of ${STREAK_TARGET} in a row for ${q.topic}.`;
    markVerified(q, node);
  } else {
    if (!st.mastered) { st.run = []; st.fresh = 0; }
    status.className = "status bad";
    status.textContent = st.mastered ? "Not all values match." : "Not all values match. Your run for this topic starts again.";
  }
  saveProgress();
  renderTopics();
}

// ---------- timer ----------
function timer(minutes) {
  let left = minutes * 60, id = null;
  const display = el("span", { class: "time" });
  const startBtn = el("button", { type: "button", class: "btn" }, "Start");
  const resetBtn = el("button", { type: "button", class: "btn ghost" }, "Reset");
  const msg = el("span", { class: "sr-only", role: "status" });
  const box = el("div", { class: "timer" }, display, startBtn, resetBtn, msg);
  const show = () => {
    const a = Math.abs(left), s = `${Math.floor(a / 60)}:${String(a % 60).padStart(2, "0")}`;
    display.textContent = left < 0 ? `+${s} over` : s;
    box.classList.toggle("over", left < 0);
  };
  const stop = () => { clearInterval(id); id = null; startBtn.textContent = "Start"; };
  startBtn.onclick = () => {
    if (id) return stop();
    startBtn.textContent = "Pause";
    id = setInterval(() => {
      if (!document.body.contains(box)) return stop();
      left--; show();
      if (left === 0) msg.textContent = "Time is up.";
    }, 1000);
  };
  resetBtn.onclick = () => { stop(); left = minutes * 60; msg.textContent = ""; show(); };
  show();
  return box;
}

// ---------- views ----------
const filters = { subject: "", topic: "", source: "", text: "", hideVerified: false };

function viewBank(view) {
  const select = (key, label, opts) => el("label", { class: "filter" }, el("span", {}, label),
    el("select", { onchange: e => { filters[key] = e.target.value; draw(); } },
      el("option", { value: "" }, "All"), ...opts.map(o => el("option", { value: o, selected: filters[key] === o }, o))));
  const bar = el("div", { class: "filters" },
    select("subject", "Subject", ["Excel", "SQL"]),
    select("topic", "Topic", D.topics),
    select("source", "Source", sources()),
    el("label", { class: "filter grow" }, el("span", {}, "Search"),
      el("input", { type: "search", value: filters.text, placeholder: "e.g. duplicate, join, 2014", oninput: e => { filters.text = e.target.value; draw(); } })),
    el("label", { class: "check-inline" },
      el("input", { type: "checkbox", checked: filters.hideVerified, onchange: e => { filters.hideVerified = e.target.checked; draw(); } }),
      " Hide verified"));
  const count = el("p", { class: "muted small count" });
  const list = el("div", { class: "questions" });
  view.append(el("h1", { class: "view-title" }, "Question bank"),
    el("p", { class: "lead" }, "Excel and SQL tasks built only from the course materials. Each one has a \"Check my result\" box: type in a few figures from your output (row count, a control total, a top value) and see if they match."),
    bar, count, list);
  function draw() {
    const t = filters.text.trim().toLowerCase();
    const qs = D.bank.filter(q => (!filters.subject || q.subject === filters.subject) && (!filters.topic || q.topic === filters.topic)
      && (!filters.source || q.source === filters.source) && (!filters.hideVerified || !progress.verified[q.id])
      && (!t || `${q.id} ${q.prompt} ${q.source} ${q.topic}`.toLowerCase().includes(t)));
    count.textContent = `${qs.length} of ${D.bank.length} questions`;
    list.replaceChildren(...qs.map(q => questionCard(q)));
  }
  draw();
}

let lastExam = null;
function viewExamList(view) {
  const choose = () => {
    const pool = D.exams.filter(e => e.id !== lastExam);
    location.hash = `#/exam/${pool[Math.floor(Math.random() * pool.length)].id}`;
  };
  const verifiedIn = e => e.questions.filter(id => progress.verified[id]).length;
  view.append(el("h1", { class: "view-title" }, "Practice exams"),
    el("p", { class: "lead" }, `${D.exams.length} full data manipulation exams in the oral exam format: 5 questions, Excel and SQL, one Excel case and one SQL case, 8 minutes. Every answer can be checked. Longer assignment-style tasks are in the question bank.`),
    el("button", { class: "btn", type: "button", onclick: choose }, "Choose one for me"),
    el("div", { class: "exam-grid" }, ...D.exams.map(e => el("a", { class: "exam-tile", href: `#/exam/${e.id}` },
      el("strong", {}, e.id), el("span", {}, `${e.excel} + ${e.sql}`),
      el("span", { class: "muted small" }, `${e.minutes} min · ${verifiedIn(e)} of 5 verified`)))));
}

function viewExam(view, id) {
  const e = D.exams.find(x => x.id === id);
  if (!e) return viewExamList(view);
  lastExam = id;
  const qs = e.questions.map(q => D.byId[q]);
  let cur = 0;
  const score = el("span", { class: "score" });
  const steps = el("div", { class: "steps", role: "tablist", "aria-label": "Exam questions" });
  const prev = el("button", { type: "button", class: "btn ghost", onclick: () => go(cur - 1) }, "← Previous");
  const next = el("button", { type: "button", class: "btn ghost", onclick: () => go(cur + 1) }, "Next →");
  const cards = qs.map((q, i) => {
    const c = questionCard(q, upd);
    c.prepend(el("div", { class: "qnum" }, `Question ${i + 1} of ${qs.length}`));
    return c;
  });
  function upd() {
    score.textContent = `${qs.filter(q => progress.verified[q.id]).length} of ${qs.length} verified`;
    steps.replaceChildren(...qs.map((q, i) => el("button", {
      type: "button", role: "tab", class: `step${i === cur ? " cur" : ""}${progress.verified[q.id] ? " ok" : ""}`,
      "aria-selected": String(i === cur), "aria-label": `Question ${i + 1}${progress.verified[q.id] ? ", verified" : ""}`,
      onclick: () => go(i) }, progress.verified[q.id] ? "✓" : String(i + 1))));
  }
  function go(i) {
    cur = Math.max(0, Math.min(qs.length - 1, i));
    cards.forEach((c, k) => { c.hidden = k !== cur; });
    prev.disabled = cur === 0;
    next.disabled = cur === qs.length - 1;
    upd();
  }
  const fileLinks = e.files.map(f => el("a", { href: `files/${f}`, download: "" }, f));
  const dlStatus = el("span", { class: "muted small", role: "status" });
  const dlAll = el("button", { type: "button", class: "btn", onclick: async () => {
    dlAll.disabled = true;
    for (const [i, a] of fileLinks.entries()) {
      dlStatus.textContent = `Starting download ${i + 1} of ${fileLinks.length}…`;
      a.click();
      await new Promise(r => setTimeout(r, 700)); // browsers block rapid multiple downloads
    }
    dlStatus.textContent = "Downloads started. If your browser blocked some, use the links.";
    dlAll.disabled = false;
  } }, "Download all exam files");
  view.append(el("a", { class: "back", href: "#/exams" }, "← All practice exams"),
    el("h1", { class: "view-title" }, `Exam ${e.id}`),
    el("p", { class: "lead" }, `${e.excel} (Excel) + ${e.sql} (SQL). Exam time: ${e.minutes} minutes, as in the oral exam.`),
    el("div", { class: "exam-bar" }, timer(e.minutes), score),
    el("div", { class: "files-all" }, el("div", { class: "actions" }, dlAll, dlStatus),
      el("div", { class: "downloads" }, el("span", { class: "muted small" }, "Files:"), ...fileLinks)),
    el("div", { class: "exam-nav" }, prev, steps, next),
    el("div", { class: "questions" }, ...cards));
  go(0);
}

function viewRegList(view) {
  view.append(el("h1", { class: "view-title" }, "Data interpretation"),
    el("p", { class: "lead" }, "Regression exams from the restaurant case (Larry's Commissary). Daily sales are merged with the weather and game data. Read the Excel output, answer the four questions in 5 minutes, as in the oral exam, then compare with the model answers."),
    el("button", { class: "btn", type: "button", onclick: () => { location.hash = `#/reg/${D.reg[Math.floor(Math.random() * D.reg.length)].id}`; } }, "Choose one for me"),
    el("div", { class: "exam-grid" }, ...D.reg.map(r => el("a", { class: "exam-tile", href: `#/reg/${r.id}` },
      el("strong", {}, r.id), el("span", {}, r.title), el("span", { class: "muted small" }, `4 questions · ${r.minutes} min`)))));
}

function fmt(v, kind) {
  if (kind === "int") return Math.round(v).toLocaleString("en-US");
  if (kind === "p") return v === 0 ? "0" : Math.abs(v) < 0.0001 ? v.toExponential(2).toUpperCase() : v.toFixed(4);
  if (kind === "big") return v.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  return v.toLocaleString("en-US", { maximumFractionDigits: 4, minimumFractionDigits: 4 });
}

function viewReg(view, id) {
  const r = D.reg.find(x => x.id === id);
  if (!r) return viewRegList(view);
  const o = r.output;
  const table = (cap, head, rows) => el("div", { class: "tbl-wrap" }, el("table", { class: "out" },
    el("caption", {}, cap), el("thead", {}, el("tr", {}, ...head.map(h => el("th", { scope: "col" }, h)))),
    el("tbody", {}, ...rows.map(row => el("tr", {}, ...row.map((c, i) => i === 0 ? el("th", { scope: "row" }, c) : el("td", {}, c)))))));
  const a = o.anova;
  view.append(el("a", { class: "back", href: "#/interpretation" }, "← All interpretation exams"),
    el("h1", { class: "view-title" }, `${r.id}: ${r.title}`),
    el("p", { class: "lead" }, r.scenario),
    el("div", { class: "exam-bar" }, timer(r.minutes),
      el("span", { class: "downloads" }, el("span", { class: "muted small" }, "Data:"), el("a", { href: `files/${r.file}`, download: "" }, r.file))),
    el("p", { class: "muted small" }, `Model: ${o.formula.replace("~", "=")}. SUMMARY OUTPUT as in Excel's Data Analysis → Regression.`),
    table("Regression Statistics", ["", "Value"], o.stats.map(([k, v]) => [k, k === "Observations" ? fmt(v, "int") : k === "Standard Error" ? fmt(v, "big") : fmt(v)])),
    table("ANOVA", ["", "df", "SS", "MS", "F", "Significance F"], [
      ["Regression", a.df_reg, fmt(a.ss_reg, "big"), fmt(a.ss_reg / a.df_reg, "big"), fmt(a.F), fmt(a.sigF, "p")],
      ["Residual", a.df_res, fmt(a.ss_res, "big"), fmt(a.ss_res / a.df_res, "big"), "", ""],
      ["Total", a.df_reg + a.df_res, fmt(a.ss_reg + a.ss_res, "big"), "", "", ""]]),
    table("Coefficients", ["", "Coefficients", "Standard Error", "t Stat", "P-value", "Lower 95%", "Upper 95%"],
      o.coefs.map(([n, b, se, t, p, lo, hi]) => [n, fmt(b), fmt(se), fmt(t), fmt(p, "p"), fmt(lo), fmt(hi)])),
    el("ol", { class: "reg-qs" }, ...r.questions.map(q => {
      const ans = el("p", { class: "answer", hidden: true }, q.a);
      const btn = el("button", { class: "btn ghost", type: "button", "aria-expanded": "false",
        onclick: () => { ans.hidden = !ans.hidden; btn.textContent = ans.hidden ? "Show answer" : "Hide answer"; btn.setAttribute("aria-expanded", String(!ans.hidden)); } }, "Show answer");
      return el("li", {}, el("p", { class: "rq" }, q.q), btn, ans);
    })));
}

// ---------- router ----------
function render() {
  const [, section = "bank", id] = (location.hash || "#/bank").split("/");
  const tab = { bank: "bank", exams: "exams", exam: "exams", interpretation: "interpretation", reg: "interpretation" }[section] || "bank";
  document.querySelectorAll(".tabs a").forEach(a => a.classList.toggle("active", a.dataset.tab === tab));
  $("#layout").classList.toggle("no-panel", tab === "interpretation");
  const view = $("#view");
  view.replaceChildren();
  if (section === "exam") viewExam(view, id);
  else if (section === "exams") viewExamList(view);
  else if (section === "reg") viewReg(view, id);
  else if (section === "interpretation") viewRegList(view);
  else viewBank(view);
  renderTopics();
  window.scrollTo(0, 0);
}

$("#reset").addEventListener("click", () => {
  if (!confirmReset()) return;
  progress = { verified: {}, topics: {} };
  saveProgress();
  render();
});
// Two-step reset without a browser dialog.
let resetArmed = false;
function confirmReset() {
  const b = $("#reset");
  if (resetArmed) { resetArmed = false; b.textContent = "Reset my progress"; return true; }
  resetArmed = true;
  b.textContent = "Click again to confirm reset";
  setTimeout(() => { resetArmed = false; b.textContent = "Reset my progress"; }, 4000);
  return false;
}

window.addEventListener("hashchange", render);
if (window.matchMedia("(max-width: 860px)").matches) $("#topics-box").open = false; // phones: topics collapsed under the summary
Promise.all(["questions", "exams", "regression", "schemas"].map(n => fetch(`data/${n}.json`).then(r => r.json())))
  .then(([q, e, r, s]) => {
    D.schemas = s;
    D.salt = q.salt;
    D.topics = q.topics;
    D.bank = q.questions;
    D.byId = Object.fromEntries(q.questions.map(x => [x.id, x]));
    D.exams = e.exams;
    D.reg = r.exams;
    render();
  });
