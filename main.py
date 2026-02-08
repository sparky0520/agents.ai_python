from typing import Dict, List, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import dynamic loader
from agent_loader import loader

# Load environment variables (fallback if not provided in request)
load_dotenv()


# --- 1. Data Models for API ---


class AgentRequest(BaseModel):
    agent_id: str
    agent_config: Dict[str, str] = {}
    auth_requirements: Dict[str, List[Dict[str, str]]] = {}

    # We use Dict for env and inputs because their structure depends on the agent
    env: Dict[str, Any]
    inputs: Dict[str, Any]


# --- 2. FastAPI App ---
app = FastAPI(title="AI Agent Orchestrator", version="0.1.0")

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
    print(f"Received Request for agent {request.agent_id}")

    try:
        # Dynamically load the agent module
        agent_module = loader.get_agent_module(request.agent_id)

        # Check if module has required attributes
        if (
            not hasattr(agent_module, "get_initial_state")
            or not hasattr(agent_module, "agent_graph")
            or not hasattr(agent_module, "get_result")
        ):
            raise ValueError(
                f"Agent module for {request.agent_id} is missing required exports (get_initial_state, agent_graph, get_result)"
            )

        # Prepare initial state using specific agent's helper
        # We need to map the generic Dict inputs to what the agent expects if needed
        # safely assuming the agent module handles the dicts or pydantic models if we pass dicts

        # Reconstruct AgentEnv and AgentInputs from the request dicts if the agent uses Pydantic
        # For now, we assume get_initial_state can handle dicts or we need to look at how it was imported.
        # The previous code imported AgentEnv, AgentInputs classes.
        # Now we don't have them imported statically.

        # We can try to instantiate them from the module if they exist
        env = request.env
        inputs = request.inputs

        if hasattr(agent_module, "AgentEnv"):
            # Convert dict to pydantic object
            env = agent_module.AgentEnv(**request.env)

        if hasattr(agent_module, "AgentInputs"):
            inputs = agent_module.AgentInputs(**request.inputs)

        initial_state = agent_module.get_initial_state(env, inputs)

        # Invoke the graph
        final_output = agent_module.agent_graph.invoke(initial_state)

        # Return results using specific agent's helper
        return agent_module.get_result(final_output)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Use standard uvicorn execution
    uvicorn.run(app, host="0.0.0.0", port=8000)
