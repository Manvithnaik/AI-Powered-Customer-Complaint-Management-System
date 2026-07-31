const BASE = '';  // Vite proxy routes /api/* to FastAPI

export async function analyzeComplaintText(text) {
  const res = await fetch(`${BASE}/api/ai/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${res.status}`);
  }
  return res.json();
}

export async function analyzeComplaintFile(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/api/ai/analyze-file`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${res.status}`);
  }
  return res.json();
}

export async function saveComplaint(data) {
  // Convert empty strings to null for optional fields
  const payload = Object.fromEntries(
    Object.entries(data).map(([k, v]) => [k, v === '' ? null : v])
  );
  const res = await fetch(`${BASE}/api/complaints/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${res.status}`);
  }
  return res.json();
}

export async function listComplaints(skip = 0, limit = 50) {
  const res = await fetch(`${BASE}/api/complaints/?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}
