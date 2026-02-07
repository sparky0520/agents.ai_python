from typing import Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import specific agent definition
from agent_package.reddit_scout import (
    agent_graph,
    AgentEnv,
    AgentInputs,
    get_initial_state,
    get_result,
)

# Load environment variables (fallback if not provided in request)
load_dotenv()


# --- 1. Data Models for API ---
# AgentEnv and AgentInputs are imported from the agent module


class AgentRequest(BaseModel):
    agent_config: Dict[str, str] = {}
    auth_requirements: Dict[str, List[Dict[str, str]]] = {}

    env: AgentEnv
    inputs: AgentInputs


# --- 2. FastAPI App ---
app = FastAPI(title="Reddit Scout Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation Error: {exc}")
    try:
        body = await request.json()
        print(f"Request Body: {body}")
    except Exception:
        print("Could not parse body")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc)},
    )


@app.post("/execute")
def execute_agent(request: AgentRequest):
    """
    Executes the Agent with provided credentials and inputs.
    """
    print(f"Received Request: {request.model_dump_json(indent=2)}")

    try:
        # Prepare initial state using specific agent's helper
        initial_state = get_initial_state(request.env, request.inputs)

        # Invoke the graph
        final_output = agent_graph.invoke(initial_state)

        # Return results using specific agent's helper
        return get_result(final_output)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Use standard uvicorn execution
    uvicorn.run(app, host="0.0.0.0", port=8000)
