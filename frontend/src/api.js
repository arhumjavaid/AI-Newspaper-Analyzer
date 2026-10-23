// Thin API client for the FastAPI backend.

export async function getHealth() {
  const r = await fetch("/api/health");
  if (!r.ok) throw new Error("Health check failed");
  return r.json();
}

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: form });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${r.status})`);
  }
  return r.json();
}

export async function analyzeText(text, sourceName) {
  const r = await fetch("/api/analyze-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_name: sourceName || null }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || `Analysis failed (${r.status})`);
  }
  return r.json();
}

export async function getUploads() {
  const r = await fetch("/api/uploads");
  if (!r.ok) throw new Error("Failed to load uploads");
  return r.json();
}

export async function getUpload(id) {
  const r = await fetch(`/api/uploads/${id}`);
  if (!r.ok) throw new Error("Failed to load analysis");
  return r.json();
}

export async function deleteUpload(id) {
  const r = await fetch(`/api/uploads/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to delete analysis");
  return r.json();
}

export async function getTrends() {
  const r = await fetch("/api/trends");
  if (!r.ok) throw new Error("Failed to load trends");
  return r.json();
}
