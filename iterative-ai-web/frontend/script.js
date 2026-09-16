// ==========================================
// CONFIG — change this to your deployed backend URL
// ==========================================
const API_URL = "https://iteraai-backend.onrender.com"; // e.g. "https://your-app.onrender.com" after deployment

// ==========================================
// ELEMENTS
// ==========================================
const topicInput = document.getElementById("topic-input");
const charCount = document.getElementById("char-count");
const clearBtn = document.getElementById("clear-btn");
const generateBtn = document.getElementById("generate-btn");

const loadingBox = document.getElementById("loading-box");
const loadingText = document.getElementById("loading-text");
const errorBox = document.getElementById("error-box");
const resultCard = document.getElementById("result-card");

const verdictPill = document.getElementById("verdict-pill");
const resultPost = document.getElementById("result-post");
const statAttempts = document.getElementById("stat-attempts");
const statWords = document.getElementById("stat-words");
const statApproved = document.getElementById("stat-approved");
const resultFeedback = document.getElementById("result-feedback");

const copyBtn = document.getElementById("copy-btn");
const downloadBtn = document.getElementById("download-btn");
const newTopicBtn = document.getElementById("new-topic-btn");

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

let lastDraft = "";

// ==========================================
// CHARACTER COUNTER
// ==========================================
topicInput.addEventListener("input", () => {
  charCount.textContent = `${topicInput.value.length}/200 characters`;
});

// ==========================================
// CLEAR BUTTON
// ==========================================
clearBtn.addEventListener("click", () => {
  topicInput.value = "";
  charCount.textContent = "0/200 characters";
  topicInput.focus();
});

// ==========================================
// HEALTH CHECK (on page load)
// ==========================================
async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`);
    const data = await res.json();
    if (data.configured) {
      statusDot.classList.remove("offline");
      statusText.textContent = "AI Engine Online";
    } else {
      statusDot.classList.add("offline");
      statusText.textContent = "Configuration Needed";
    }
  } catch (err) {
    statusDot.classList.add("offline");
    statusText.textContent = "Backend Unreachable";
  }
}
checkHealth();

// ==========================================
// GENERATE
// ==========================================
generateBtn.addEventListener("click", async () => {
  const topic = topicInput.value.trim();

  hide(errorBox);
  hide(resultCard);

  if (!topic) {
    showError("Please enter a topic before generating.");
    return;
  }

  setLoading(true);

  try {
    const res = await fetch(`${API_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || "Something went wrong while generating your post. Please try again.");
      return;
    }

    renderResult(data);
  } catch (err) {
    showError(
      "Couldn't reach the AI backend. Make sure the API server is running " +
      `and API_URL in script.js points to it (currently: ${API_URL}).`
    );
  } finally {
    setLoading(false);
  }
});

// ==========================================
// RENDER RESULT
// ==========================================
function renderResult(data) {
  lastDraft = data.draft || "";

  verdictPill.textContent = data.is_approved ? "Approved" : "Max attempts reached";
  verdictPill.className = "verdict-pill " + (data.is_approved ? "approved" : "rejected");

  resultPost.textContent = lastDraft;

  statAttempts.textContent = data.attempt;
  statWords.textContent = lastDraft.trim().split(/\s+/).filter(Boolean).length;
  statApproved.textContent = data.is_approved ? "Yes" : "No";

  resultFeedback.textContent = data.review_feedback || "—";

  show(resultCard);
}

// ==========================================
// COPY / DOWNLOAD / RESET
// ==========================================
copyBtn.addEventListener("click", async () => {
  if (!lastDraft) return;
  await navigator.clipboard.writeText(lastDraft);
  const original = copyBtn.textContent;
  copyBtn.textContent = "Copied!";
  setTimeout(() => (copyBtn.textContent = original), 1500);
});

downloadBtn.addEventListener("click", () => {
  if (!lastDraft) return;
  const blob = new Blob([lastDraft], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "linkedin_post.txt";
  a.click();
  URL.revokeObjectURL(url);
});

newTopicBtn.addEventListener("click", () => {
  topicInput.value = "";
  charCount.textContent = "0/200 characters";
  hide(resultCard);
  hide(errorBox);
  topicInput.focus();
});

// ==========================================
// HELPERS
// ==========================================
function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  clearBtn.disabled = isLoading;
  if (isLoading) {
    loadingText.textContent = "Generating your post — writer and reviewer are working on it...";
    show(loadingBox);
  } else {
    hide(loadingBox);
  }
}

function showError(message) {
  errorBox.textContent = message;
  show(errorBox);
}

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }
