// Vercel serverless function: result-aware AI tutor (Gemini).
// The API key lives in the Vercel environment variable GEMINI_API_KEY and never reaches the browser.
// The tutor never receives the correct answers: the site only has hashes of them.

// Light models first: fast and rarely overloaded, and good enough for short hints.
const MODELS = [process.env.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"].filter(Boolean);
const LIMITS = { message: 3000, history: 6, turn: 2000, context: 12000 };

const SYSTEM = `You are a tutor for the university course "Data Analytics in Accounting" (SDU). A student is practising Excel and SQL tasks for an oral exam.

Rules:
1. Never give the final figures. Never write the formula or query for the student: not the full solution, and not a corrected version of their own attempt, not even one corrected line or clause. Describe the change in words and name the function, operator or clause (e.g. "use > instead of >=", "add a GROUP BY on the cardholder"), then let the student write it. If an example really helps, use a different table and different columns from the task.
2. You do not know the correct answer values, so never guess them or say a number is right. The VERIFICATION section is the truth: a figure marked MATCHES is correct; a figure marked DOES NOT MATCH is wrong, even if the student's formula or query looks fine to you. Use any known-mistake hint as the starting point.
3. Use only the sheet, table and column names in the DATASET section. Excel: English function names. SQL: SQLite syntax (no YEAR(), DATEDIFF(), TOP; use strftime, julianday, LIMIT).
4. Be short: at most about 120 words, plain sentences, code in backticks.
5. If the student asks for the answer, the numbers or the full formula/query, say briefly that you can't give it, then give the next hint in words only, with no formula or query in that reply.
6. If all figures match, confirm briefly and, if useful, mention a faster or more robust way to do it.`;

function clip(s, n) {
  s = String(s ?? "");
  return s.length > n ? s.slice(0, n) + " [cut]" : s;
}

function buildContext(b) {
  const checks = (b.checks || []).slice(0, 6).map(c => {
    const state = c.state === "ok" ? "MATCHES" : c.state === "none" ? "not checked yet" : "DOES NOT MATCH";
    const typed = c.value ? ` (student typed: ${clip(c.value, 60)})` : "";
    const hint = c.hint ? ` Known-mistake hint shown: ${clip(c.hint, 300)}` : "";
    return `- ${clip(c.label, 120)}: ${state}${typed}.${hint}`;
  }).join("\n");
  return clip(`TASK (${clip(b.subject, 10)}, ${clip(b.source, 60)}, topic: ${clip(b.topic, 60)}):
${clip(b.prompt, 1200)}
${b.note ? "Task note: " + clip(b.note, 400) : ""}

DATASET:
${clip(b.datasets, 6000)}

VERIFICATION (from the site's answer check):
${checks || "- The student has not checked any figures yet."}`, LIMITS.context);
}

async function callGemini(model, key, system, contents, timeoutMs) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents,
        generationConfig: { temperature: 0.3, maxOutputTokens: 700 },
      }),
      signal: ctrl.signal,
    });
    const data = await r.json().catch(() => ({}));
    return { status: r.status, data };
  } catch (e) {
    if (e && e.name === "AbortError") return { status: 0, timedOut: true, data: {} };
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "Use POST." });
  const key = process.env.GEMINI_API_KEY;
  if (!key) return res.status(503).json({ error: "The AI tutor is not configured yet (missing GEMINI_API_KEY)." });

  const b = req.body || {};
  const message = String(b.message || "").trim();
  if (!message) return res.status(400).json({ error: "Write a question for the tutor first." });

  const history = (Array.isArray(b.history) ? b.history : []).slice(-LIMITS.history)
    .filter(t => t && (t.role === "user" || t.role === "model"))
    .map(t => ({ role: t.role, parts: [{ text: clip(t.text, LIMITS.turn) }] }));
  const contents = [
    { role: "user", parts: [{ text: buildContext(b) }] },
    { role: "model", parts: [{ text: "Understood. I will follow the rules and use the verification result." }] },
    ...history,
    { role: "user", parts: [{ text: clip(message, LIMITS.message) }] },
  ];

  // Free Gemini models are sometimes overloaded: they answer 503, or hang without answering.
  // Each attempt gets its own time limit, and the whole request must finish well inside
  // Vercel's 30-second limit. Plan: main model once, then the lighter model up to twice.
  const models = [...new Set(MODELS)];
  const plan = [models[0], ...models.slice(1).flatMap(m => [m, m])];
  const deadline = Date.now() + 25000;
  const skip = new Set();
  let busy = false, limited = false;
  try {
    for (let i = 0; i < plan.length; i++) {
      const model = plan[i];
      if (skip.has(model)) continue;
      const left = deadline - Date.now();
      if (left < 3000) break;
      const { status, data, timedOut } = await callGemini(model, key, SYSTEM, contents, Math.min(9000, left - 500));
      if (status === 200) {
        const cand = data.candidates && data.candidates[0];
        const text = cand && cand.content && (cand.content.parts || []).map(p => p.text || "").join("").trim();
        if (!text) return res.status(502).json({ error: "The AI service returned an empty answer. Try rephrasing." });
        return res.status(200).json({ reply: text, truncated: cand.finishReason === "MAX_TOKENS", model });
      }
      console.error(`Gemini ${model}: ${timedOut ? "no answer within time limit" : status} ${data.error ? data.error.message : ""}`);
      if (status === 400 || status === 401 || status === 403) {
        return res.status(502).json({ error: "The AI service rejected the request. Check GEMINI_API_KEY in Vercel." });
      }
      if (timedOut || status === 503 || status === 500 || status === 504) { busy = true; }
      else { skip.add(model); if (status === 429) limited = true; }      // 404/429: don't retry this model
      if (plan[i + 1] === model && !skip.has(model)) await new Promise(r => setTimeout(r, 700));
    }
  } catch (e) {
    console.error("Gemini fetch failed:", e && e.message);
    return res.status(502).json({ error: "Could not reach the AI service. Try again." });
  }
  if (busy) return res.status(503).json({ error: "The AI service is busy right now. Try again in a moment." });
  if (limited) return res.status(429).json({ error: "The AI tutor has reached its usage limit for now. Try again in a minute." });
  return res.status(502).json({ error: "No configured Gemini model is available. Set GEMINI_MODEL in Vercel." });
};
