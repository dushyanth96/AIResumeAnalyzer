const form = document.querySelector("#api-keys-form");
const savedStatus = document.querySelector("#saved-status");
const clearButton = document.querySelector("#clear-keys");

const STORAGE_KEYS = {
  gemini: "resumeAnalyzer.geminiApiKey",
  openai: "resumeAnalyzer.openaiApiKey",
  hf: "resumeAnalyzer.hfToken",
};

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

document.querySelectorAll("[data-url]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.getAttribute("data-url");
    if (target) {
      window.open(target, "_blank", "noreferrer");
    }
  });
});

function setFieldValue(name, value) {
  const input = form.elements.namedItem(name);
  if (input) {
    input.value = value || "";
  }
}

function loadSavedKeys() {
  setFieldValue("gemini_api_key", localStorage.getItem(STORAGE_KEYS.gemini));
  setFieldValue("openai_api_key", localStorage.getItem(STORAGE_KEYS.openai));
  setFieldValue("hf_token", localStorage.getItem(STORAGE_KEYS.hf));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);

  localStorage.setItem(STORAGE_KEYS.gemini, data.get("gemini_api_key").toString().trim());
  localStorage.setItem(STORAGE_KEYS.openai, data.get("openai_api_key").toString().trim());
  localStorage.setItem(STORAGE_KEYS.hf, data.get("hf_token").toString().trim());

  savedStatus.textContent = "Keys saved locally in this browser.";
});

clearButton.addEventListener("click", () => {
  Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key));
  loadSavedKeys();
  savedStatus.textContent = "Saved keys cleared.";
});

loadSavedKeys();