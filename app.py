import hashlib
import json
import secrets
import threading
import uuid
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="방명록")

DATA_FILE = Path(__file__).parent / "guestboard.json"
_lock = threading.Lock()


class EntryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    message: str = Field(..., min_length=1, max_length=500)
    password: str = Field("", max_length=50)


class EntryDelete(BaseModel):
    password: str = Field("", max_length=50)


def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def public_entry(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "name": entry["name"],
        "message": entry["message"],
        "created_at": entry["created_at"],
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


@app.get("/api/entries")
def list_entries():
    with _lock:
        entries = load_entries()
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return {"count": len(entries), "entries": [public_entry(e) for e in entries]}


@app.post("/api/entries")
def create_entry(payload: EntryCreate, request: Request):
    name = payload.name.strip()
    message = payload.message.strip()
    if not name or not message:
        raise HTTPException(status_code=400, detail="이름과 메시지를 모두 입력해주세요.")

    salt = secrets.token_hex(8)
    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "message": message,
        "password_hash": hash_password(payload.password, salt),
        "salt": salt,
        "ip": get_client_ip(request),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    with _lock:
        entries = load_entries()
        entries.append(entry)
        save_entries(entries)

    return public_entry(entry)


@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: str, payload: EntryDelete):
    with _lock:
        entries = load_entries()
        target = next((e for e in entries if e["id"] == entry_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다.")

        if hash_password(payload.password, target["salt"]) != target["password_hash"]:
            raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")

        entries.remove(target)
        save_entries(entries)

    return {"message": "삭제되었습니다."}


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>방명록</title>
<style>
  :root {
    --green-50: #f0fdf4;
    --green-100: #dcfce7;
    --green-200: #bbf7d0;
    --green-500: #22c55e;
    --green-600: #16a34a;
    --green-700: #15803d;
    --green-900: #14532d;
  }
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", -apple-system, "Malgun Gothic", sans-serif;
    margin: 0;
    padding: 40px 16px 80px;
    background: linear-gradient(180deg, var(--green-50) 0%, #ffffff 320px);
    color: #1f2937;
  }
  .container {
    max-width: 640px;
    margin: 0 auto;
  }
  header {
    text-align: center;
    margin-bottom: 32px;
  }
  header h1 {
    margin: 0 0 8px;
    font-size: 2rem;
    color: var(--green-700);
    letter-spacing: -0.5px;
  }
  header p {
    margin: 0;
    color: #4b5563;
  }
  .card {
    background: #ffffff;
    border: 1px solid var(--green-200);
    border-radius: 16px;
    box-shadow: 0 4px 16px rgba(22, 163, 74, 0.08);
    padding: 24px;
  }
  .form-card { margin-bottom: 32px; }
  .form-row {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
  }
  input, textarea {
    width: 100%;
    font-family: inherit;
    font-size: 1rem;
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    outline: none;
    transition: border-color 0.15s;
  }
  input:focus, textarea:focus {
    border-color: var(--green-500);
  }
  textarea {
    resize: vertical;
    min-height: 90px;
    margin-bottom: 8px;
  }
  .char-count {
    text-align: right;
    font-size: 0.8rem;
    color: #9ca3af;
    margin-bottom: 12px;
  }
  .submit-btn {
    width: 100%;
    padding: 12px;
    font-size: 1rem;
    font-weight: 600;
    color: #ffffff;
    background: var(--green-600);
    border: none;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .submit-btn:hover { background: var(--green-700); }
  .submit-btn:disabled { background: #a7d9b8; cursor: not-allowed; }

  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 16px;
  }
  .list-header h2 {
    font-size: 1.1rem;
    color: var(--green-900);
    margin: 0;
  }
  .list-header span {
    color: #6b7280;
    font-size: 0.9rem;
  }
  .entry {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 4px solid var(--green-500);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
  }
  .entry-top {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--green-100);
    color: var(--green-700);
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .entry-name {
    font-weight: 600;
    color: #111827;
  }
  .entry-date {
    margin-left: auto;
    color: #9ca3af;
    font-size: 0.8rem;
  }
  .entry-message {
    white-space: pre-wrap;
    line-height: 1.5;
    color: #374151;
    margin: 0 0 8px;
  }
  .entry-actions { text-align: right; }
  .delete-btn {
    border: none;
    background: none;
    color: #9ca3af;
    font-size: 0.8rem;
    cursor: pointer;
    padding: 2px 4px;
  }
  .delete-btn:hover { color: #dc2626; }
  .empty {
    text-align: center;
    color: #9ca3af;
    padding: 40px 0;
  }
</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>방명록</h1>
      <p>다녀가신 흔적을 자유롭게 남겨주세요.</p>
    </header>

    <div class="card form-card">
      <form id="entryForm">
        <div class="form-row">
          <input id="nameInput" type="text" placeholder="이름" maxlength="20" required>
          <input id="passwordInput" type="password" placeholder="비밀번호 (삭제 시 필요)" maxlength="50">
        </div>
        <textarea id="messageInput" placeholder="방명록에 남길 메시지를 적어주세요." maxlength="500" required></textarea>
        <div class="char-count"><span id="charCount">0</span>/500</div>
        <button type="submit" class="submit-btn">방명록 남기기</button>
      </form>
    </div>

    <div class="list-header">
      <h2>남겨진 글</h2>
      <span id="countLabel"></span>
    </div>
    <div id="entryList"></div>
  </div>

<script>
const form = document.getElementById("entryForm");
const nameInput = document.getElementById("nameInput");
const passwordInput = document.getElementById("passwordInput");
const messageInput = document.getElementById("messageInput");
const charCount = document.getElementById("charCount");
const entryList = document.getElementById("entryList");
const countLabel = document.getElementById("countLabel");

messageInput.addEventListener("input", () => {
  charCount.textContent = messageInput.value.length;
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderEntries(entries) {
  countLabel.textContent = `총 ${entries.length}개`;

  if (entries.length === 0) {
    entryList.innerHTML = '<div class="empty">아직 남겨진 글이 없어요. 첫 글을 남겨보세요!</div>';
    return;
  }

  entryList.innerHTML = entries.map(entry => `
    <div class="entry" data-id="${entry.id}">
      <div class="entry-top">
        <div class="avatar">${escapeHtml(entry.name.charAt(0).toUpperCase())}</div>
        <div class="entry-name">${escapeHtml(entry.name)}</div>
        <div class="entry-date">${escapeHtml(entry.created_at)}</div>
      </div>
      <p class="entry-message">${escapeHtml(entry.message)}</p>
      <div class="entry-actions">
        <button class="delete-btn" data-id="${entry.id}">삭제</button>
      </div>
    </div>
  `).join("");
}

async function loadEntries() {
  const res = await fetch("/api/entries");
  const data = await res.json();
  renderEntries(data.entries);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = form.querySelector(".submit-btn");
  submitBtn.disabled = true;

  try {
    const res = await fetch("/api/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: nameInput.value.trim(),
        message: messageInput.value.trim(),
        password: passwordInput.value,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "글을 남기지 못했습니다.");
      return;
    }

    form.reset();
    charCount.textContent = "0";
    await loadEntries();
  } finally {
    submitBtn.disabled = false;
  }
});

entryList.addEventListener("click", async (e) => {
  if (!e.target.classList.contains("delete-btn")) return;
  const id = e.target.dataset.id;
  const password = prompt("삭제하려면 작성 시 입력한 비밀번호를 입력해주세요.");
  if (password === null) return;

  const res = await fetch(`/api/entries/${id}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "삭제하지 못했습니다.");
    return;
  }

  await loadEntries();
});

loadEntries();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
