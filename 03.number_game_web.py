import random
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="숫자 맞추기 게임")

SESSION_COOKIE = "game_session"
games: dict[str, dict] = {}


class GuessRequest(BaseModel):
    guess: int


def new_game() -> dict:
    return {"answer": random.randint(1, 100), "attempts": 0}


def get_game(request: Request) -> tuple[str, dict]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id is None or session_id not in games:
        raise HTTPException(status_code=400, detail="게임을 먼저 시작해주세요.")
    return session_id, games[session_id]


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


@app.post("/api/new-game")
def start_new_game(response: Response):
    session_id = str(uuid.uuid4())
    games[session_id] = new_game()
    response.set_cookie(SESSION_COOKIE, session_id, httponly=True)
    return {"message": "1부터 100 사이의 숫자를 맞혀보세요!"}


@app.post("/api/guess")
def guess(payload: GuessRequest, request: Request):
    session_id, game = get_game(request)

    if not 1 <= payload.guess <= 100:
        raise HTTPException(status_code=400, detail="1부터 100 사이의 숫자를 입력해주세요.")

    game["attempts"] += 1
    answer = game["answer"]

    if payload.guess < answer:
        return {"result": "low", "attempts": game["attempts"]}
    if payload.guess > answer:
        return {"result": "high", "attempts": game["attempts"]}

    attempts = game["attempts"]
    if attempts <= 5:
        praise = "정말 대단해요! 최고의 기록이에요!"
    elif attempts <= 10:
        praise = "훌륭해요!"
    else:
        praise = "축하합니다, 정답을 맞히셨어요!"

    del games[session_id]
    return {"result": "correct", "attempts": attempts, "praise": praise}


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>숫자 맞추기 게임</title>
<style>
  body {
    font-family: -apple-system, "Segoe UI", sans-serif;
    max-width: 420px;
    margin: 60px auto;
    text-align: center;
    color: #222;
  }
  h1 { font-size: 1.5rem; }
  input {
    font-size: 1.2rem;
    padding: 8px 12px;
    width: 120px;
    text-align: center;
  }
  button {
    font-size: 1.1rem;
    padding: 8px 16px;
    margin-left: 8px;
    cursor: pointer;
  }
  #message {
    margin-top: 24px;
    font-size: 1.2rem;
    min-height: 2em;
  }
  #attempts {
    color: #666;
  }
</style>
</head>
<body>
  <h1>1~100 숫자 맞추기</h1>
  <div>
    <input id="guessInput" type="number" min="1" max="100" placeholder="숫자 입력">
    <button id="guessBtn">확인</button>
  </div>
  <div id="message">게임을 준비하고 있어요...</div>
  <div id="attempts"></div>
  <button id="restartBtn" style="display:none; margin-top:16px;">다시 시작</button>

<script>
const messageEl = document.getElementById("message");
const attemptsEl = document.getElementById("attempts");
const input = document.getElementById("guessInput");
const guessBtn = document.getElementById("guessBtn");
const restartBtn = document.getElementById("restartBtn");

async function startGame() {
  const res = await fetch("/api/new-game", { method: "POST" });
  const data = await res.json();
  messageEl.textContent = data.message;
  attemptsEl.textContent = "";
  input.value = "";
  input.disabled = false;
  guessBtn.disabled = false;
  restartBtn.style.display = "none";
  input.focus();
}

async function submitGuess() {
  const value = Number(input.value);
  if (!Number.isInteger(value) || value < 1 || value > 100) {
    messageEl.textContent = "1부터 100 사이의 숫자를 입력해주세요.";
    return;
  }

  const res = await fetch("/api/guess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guess: value }),
  });

  if (!res.ok) {
    const err = await res.json();
    messageEl.textContent = err.detail;
    return;
  }

  const data = await res.json();
  if (data.result === "low") {
    messageEl.textContent = "낮습니다.";
  } else if (data.result === "high") {
    messageEl.textContent = "높습니다.";
  } else {
    messageEl.textContent = `정답입니다! ${data.attempts}번 만에 맞히셨습니다. ${data.praise}`;
    input.disabled = true;
    guessBtn.disabled = true;
    restartBtn.style.display = "inline-block";
  }
  attemptsEl.textContent = data.attempts ? `시도 횟수: ${data.attempts}` : "";
}

guessBtn.addEventListener("click", submitGuess);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") submitGuess(); });
restartBtn.addEventListener("click", startGame);

startGame();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
