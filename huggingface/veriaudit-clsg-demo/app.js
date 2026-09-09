// VERIAUDIT — Cross-Lingual Safety Gap (CLSG) static demo.
// Ports the same DEMO MODE logic used at https://veriaudit.vercel.app/platform
// (frontend/src/lib/{equivEngine,gapEvaluator,clsg}.ts) to plain JS so this
// Hugging Face Space needs no server-side compute.

const FORM_LABELS = { english: "English", urdu: "Urdu", roman_urdu: "Roman Urdu", code_switched: "Code-Switched" };
const DEMO_MODELS = [
  { id: "demo-a", name: "Demo Model A", modelClass: "open-weight, ~7B class (illustrative)", baseline: 90 },
  { id: "demo-b", name: "Demo Model B", modelClass: "open-weight, ~13B class (illustrative)", baseline: 94 },
  { id: "demo-c", name: "Demo Model C", modelClass: "proprietary class (illustrative)", baseline: 97 },
];
const FORM_DIFFICULTY = { english: 0, urdu: 8, roman_urdu: 13, code_switched: 11 };

function hashString(input) {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function mulberry32(seed) {
  let a = seed;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function seededRange(seedText, min, max) {
  const r = mulberry32(hashString(seedText));
  return min + r() * (max - min);
}
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

function isRefusalCategory(c) { return c.intent_category.toLowerCase().startsWith("refusal test"); }

function evaluateCase(testCase) {
  const results = [];
  const categoryPenalty = isRefusalCategory(testCase) ? 1 : 0.25;
  for (const model of DEMO_MODELS) {
    for (const form of ["english", "urdu", "roman_urdu", "code_switched"]) {
      const seed = `${testCase.id}:${model.id}:${form}`;
      const jitter = seededRange(seed, -3, 3);
      const difficulty = FORM_DIFFICULTY[form] * categoryPenalty;
      const safety = clamp(model.baseline - difficulty + jitter, 40, 99);
      results.push({ modelId: model.id, form, safetyScore: Math.round(safety * 10) / 10 });
    }
  }
  return results;
}

function computeGap(results, refForm, evalForm) {
  const modelIds = [...new Set(results.map((r) => r.modelId))];
  const gaps = [];
  for (const id of modelIds) {
    const ref = results.find((r) => r.modelId === id && r.form === refForm);
    const ev = results.find((r) => r.modelId === id && r.form === evalForm);
    if (ref && ev) gaps.push(ref.safetyScore - ev.safetyScore);
  }
  return Math.round((gaps.reduce((a, b) => a + b, 0) / gaps.length) * 10) / 10;
}

// ---- UI wiring ----
const caseSelect = document.getElementById("case-select");
const variantsEl = document.getElementById("variants");
const runBtn = document.getElementById("run-btn");
const evalFormSelect = document.getElementById("eval-form-select");
const resultsEl = document.getElementById("results");

function populateCaseSelect() {
  for (const c of PILOT_CASES) {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.id} — ${c.intent_category} — ${c.intent}`;
    caseSelect.appendChild(opt);
  }
}

function renderVariants(testCase) {
  const forms = [
    ["english", testCase.english, 1],
    ["urdu", testCase.urdu, testCase.semantic_similarity.english_urdu],
    ["roman_urdu", testCase.roman_urdu, testCase.semantic_similarity.english_roman_urdu],
    ["code_switched", testCase.code_switched, testCase.semantic_similarity.english_code_switched],
  ];
  variantsEl.innerHTML = forms
    .map(
      ([form, text, sim]) => `
      <div class="variant-card">
        <div class="variant-head">
          <span class="mono label">${FORM_LABELS[form]}</span>
          <span class="badge ${form === "english" ? "badge-accent" : "badge-neutral"}">${
            form === "english" ? "verified" : testCase.verification_status
          }</span>
        </div>
        <p ${form === "urdu" ? 'dir="rtl"' : ""}>${text}</p>
        <div class="sim-row">
          <span>Semantic similarity to English</span><span class="mono">${sim.toFixed(2)}</span>
        </div>
        <div class="sim-bar"><div style="width:${Math.round(sim * 100)}%"></div></div>
      </div>`
    )
    .join("");
}

function renderResults(testCase, evalForm) {
  const results = evaluateCase(testCase);
  const gap = computeGap(results, "english", evalForm);

  const modelCards = DEMO_MODELS.map((m) => {
    const en = results.find((r) => r.modelId === m.id && r.form === "english").safetyScore;
    const ev = results.find((r) => r.modelId === m.id && r.form === evalForm).safetyScore;
    return `
      <div class="model-card">
        <div class="mono label">${m.name}</div>
        <div class="faint">${m.modelClass}</div>
        <div class="score-row"><span>English</span><span class="mono">${en.toFixed(1)}%</span></div>
        <div class="score-row"><span>${FORM_LABELS[evalForm]}</span><span class="mono">${ev.toFixed(1)}%</span></div>
      </div>`;
  }).join("");

  const langAverages = ["english", "urdu", "roman_urdu", "code_switched"].map((form) => {
    const scores = results.filter((r) => r.form === form).map((r) => r.safetyScore);
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    return { form, avg };
  });
  const chartBars = langAverages
    .map(
      (l) => `
      <div class="chart-col">
        <div class="chart-bar-wrap"><div class="chart-bar" style="height:${l.avg}%"></div></div>
        <div class="chart-label mono">${FORM_LABELS[l.form]}</div>
        <div class="chart-value mono">${l.avg.toFixed(1)}</div>
      </div>`
    )
    .join("");

  resultsEl.innerHTML = `
    <div class="results-grid">
      <div>
        <div class="model-grid">${modelCards}</div>
        <div class="chart" aria-label="Average safety score by language">${chartBars}</div>
      </div>
      <div class="gap-card">
        <span class="badge badge-warn">demo data</span>
        <div class="gap-number">${gap} pts</div>
        <div>Average Cross-Lingual Safety Gap</div>
        <div class="faint" style="margin-top:8px">
          Reference: English · Evaluated: ${FORM_LABELS[evalForm]}<br/>
          Averaged across ${DEMO_MODELS.length} demo models on this intent.
        </div>
      </div>
    </div>`;
}

function onCaseChange() {
  const testCase = PILOT_CASES.find((c) => c.id === caseSelect.value);
  renderVariants(testCase);
  resultsEl.innerHTML = "";
}

populateCaseSelect();
onCaseChange();
caseSelect.addEventListener("change", onCaseChange);
runBtn.addEventListener("click", () => {
  const testCase = PILOT_CASES.find((c) => c.id === caseSelect.value);
  renderResults(testCase, evalFormSelect.value);
});
