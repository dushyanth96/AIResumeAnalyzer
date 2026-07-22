const API_BASE_URL = "https://airesumeanalyzer-4hko.onrender.com";
const form = document.querySelector("#form");
const statusText = document.querySelector("#status");
const result = document.querySelector("#result");
const history = document.querySelector("#history");

document.querySelectorAll("[data-href]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.getAttribute("data-href");
    if (!target) return;
    if (target.startsWith("#")) {
      document.querySelector(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    window.location.href = target;
  });
});


const STORAGE_KEYS = {
  gemini: "resumeAnalyzer.geminiApiKey",
  openai: "resumeAnalyzer.openaiApiKey",
  hf: "resumeAnalyzer.hfToken",
};

function getStoredValue(key) {
  return localStorage.getItem(key) || "";
}


function buildApiHeaders() {
  const headers = {};
  const geminiKey = getStoredValue(STORAGE_KEYS.gemini);
  const openaiKey = getStoredValue(STORAGE_KEYS.openai);
  const hfToken = getStoredValue(STORAGE_KEYS.hf);

  if (geminiKey) headers["X-Gemini-API-Key"] = geminiKey;
  if (openaiKey) headers["X-OpenAI-API-Key"] = openaiKey;
  if (hfToken) headers["X-HF-Token"] = hfToken;

  return headers;
}

function listItems(values) {
  return values.map((value) => `<li>${value}</li>`).join("");
}

async function loadHistory() {
  const response = await fetch(`${API_BASE_URL}/api/analyses`);
  const analyses = await response.json();
  if (!Array.isArray(analyses)) {
    console.error("Expected array but got:", analyses);
    history.innerHTML = "<p>No history available</p>";
    return;
  }
  history.innerHTML = analyses
    .map(
      (analysis) => `
        <div class="history-row">
          <span>${analysis.resume_filename}</span>
          <strong>${analysis.match_score}%</strong>
        </div>
      `
    )
    .join("");
}

async function checkApi() {
  try {
    const response = await fetch(`${API_BASE_URL}/`);
    if (!response.ok) throw new Error("offline");
    statusText.textContent = "API Online";
  } catch (error) {
    statusText.textContent = `API Offline - ${error.message}`;
    console.error("API check failed:", error);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  result.textContent = "Analyzing...";
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: buildApiHeaders(),
    body: new FormData(form),
  });
  const payload = await response.json();
  if (!response.ok) {
    result.textContent = payload.detail || "Analysis failed";
    return;
  }
  result.innerHTML = `
    <h2>${payload.match_score}% match</h2>
    <p><strong>AI source:</strong> ${payload.ai_provider}</p>
    <span class="metric">Semantic ${payload.semantic_similarity}</span>
    <span class="metric">Skill ${payload.score_breakdown.skill_match}</span>
    <span class="metric">Experience ${payload.score_breakdown.experience_relevance}</span>
    <h3>AI Fit Summary</h3>
    <p>${payload.ai_summary}</p>
    <h3>Matched Skills</h3>
    <ul>${listItems(payload.matched_skills)}</ul>
    <h3>Missing Skills</h3>
    <ul>${listItems(payload.missing_skills)}</ul>
    <h3>AI Resume Recommendations</h3>
    <ul>${listItems(payload.suggestions)}</ul>
    <h3>Job Alignment Advice</h3>
    <ul>${listItems(payload.job_alignment_advice)}</ul>
    <h3>Likely Interview Questions</h3>
    <div class="question-list">
      ${payload.interview_questions
        .map(
          (item) => `
            <article class="question-card">
              <strong>${item.question}</strong>
              <p>${item.why_it_matters}</p>
              <ul>${listItems(item.strong_answer_points)}</ul>
            </article>
          `
        )
        .join("")}
    </div>
    <h3>Answer Strategy</h3>
    <ul>${listItems(payload.answer_strategy)}</ul>
    <h3>Study Plan</h3>
    <ul>${listItems(payload.study_plan)}</ul>
    <h3>Recruiter Pitch</h3>
    <p>${payload.recruiter_pitch}</p>
  `;
  await loadHistory();
});

checkApi();
loadHistory();
