from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="OpenCV Proctoring API")

# Store session violations in memory
# Format: {"session_id_1": {"warnings": 1, "terminated": False}}
session_violations = {}

class ViolationRequest(BaseModel):
    session_id: str
    student_id: str

class ViolationResponse(BaseModel):
    action: str # "warning" or "terminate"
    warnings_count: int
    message: str

@app.post("/log-violation", response_model=ViolationResponse)
async def log_camera_violation(violation: ViolationRequest):
    session_id = violation.session_id
    
    if session_id not in session_violations:
        session_violations[session_id] = {"warnings": 0, "terminated": False}
        
    session_state = session_violations[session_id]
    
    if session_state["terminated"]:
        return ViolationResponse(
            action="terminate",
            warnings_count=session_state["warnings"],
            message="Test has already been terminated."
        )
        
    session_state["warnings"] += 1
    warnings = session_state["warnings"]
    
    if warnings >= 3:
        session_state["terminated"] = True
        return ViolationResponse(
            action="terminate",
            warnings_count=warnings,
            message="FINAL WARNING: You have repeatedly looked away from the screen. The test is now terminated."
        )
    else:
        return ViolationResponse(
            action="warning",
            warnings_count=warnings,
            message=f"WARNING {warnings}/3: Please keep your eyes on the screen!"
        )

@app.post("/reset-session/{session_id}")
async def reset_session(session_id: str):
    if session_id in session_violations:
        del session_violations[session_id]
        return {"status": "success", "message": f"Session {session_id} reset."}
    return {"status": "error", "message": "Session not found."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8001, reload=True)
