"""
IteraAI API — thin FastAPI wrapper around the LangGraph writer-reviewer workflow.

Endpoints:
  GET  /health     -> {"status": "ok", "configured": true/false}
  POST /generate    -> runs the full iterative workflow and returns the final result
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from itterative_tool import build_app, initial_state, ConfigError, MAX_ATTEMPTS

app = FastAPI(title="IteraAI API")

# Allow the frontend (any origin, including plain file:// or a different
# domain once deployed) to call this API. Tighten allow_origins to your
# actual frontend URL once you know it, for better security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph_app = None
config_error_message = None


@app.on_event("startup")
def startup_event():
    global graph_app, config_error_message
    try:
        graph_app = build_app()
    except Exception as e:
        graph_app = None
        config_error_message = str(e)
        print(f"STARTUP CRASH ERROR: {repr(e)}")


class GenerateRequest(BaseModel):
    topic: str


@app.get("/health")
def health():
    return {"status": "ok", "configured": graph_app is not None}


@app.post("/generate")
def generate(req: GenerateRequest):
    topic = (req.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    if graph_app is None:
        raise HTTPException(
            status_code=500,
            detail=f"CONFIG ERROR: {config_error_message}"
        )
    try:
        result = graph_app.invoke(initial_state(topic))
    except Exception as e:
     print(f"DEBUG CRASH REASON: {repr(e)}")   
     raise HTTPException(status_code=500, detail=str(e))  

    return {
        "topic": topic,
        "draft": result["draft"],
        "attempt": result["attempt"],
        "max_attempts": MAX_ATTEMPTS,
        "is_approved": result["is_approved"],
        "review_feedback": result["review_feedback"],
    }
