from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

try:
    from .services.llm_service import run_llm
    from .states.dialog_state import DialogState, init_dialog_state
    from .states.state_transition import update_state
except ImportError:
    from services.llm_service import run_llm
    from states.dialog_state import DialogState, init_dialog_state
    from states.state_transition import update_state

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "LLM chatbot server is running"}


class ChatRequest(BaseModel):
    user_message: str
    model_result: dict[str, Any]
    state: DialogState | None = None
    dialog_summary: str | None = None


class StartRequest(BaseModel):
    model_result: dict[str, Any]


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        dialog_state = req.state or init_dialog_state()
        dialog_state = update_state(dialog_state, req.user_message)

        reply = run_llm(
            user_text=req.user_message,
            dialog_state=dialog_state,
            model_result=req.model_result,
        )

        return {
            "response": reply,
            "state": dialog_state.model_dump(),
            "dialog_summary": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start")
async def start_chat(req: StartRequest):
    try:
        dialog_state = init_dialog_state()
        reply = run_llm(
            user_text="사용자가 아직 아무 말도 하지 않았다. 오늘 대화를 자연스럽게 시작해라.",
            dialog_state=dialog_state,
            model_result=req.model_result,
        )

        return {
            "response": reply,
            "state": dialog_state.model_dump(),
            "dialog_summary": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
