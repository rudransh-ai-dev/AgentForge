from core.router import route_task_async
from agents.coder import run_coder_async
from agents.analyst import run_analyst_async

async def run_orchestration_async(prompt: str):
    # Backward compatibility if needed, but the main.py manages this now
    decision = await route_task_async(prompt)
    route = decision.get("selected_agent", "analyst")
    
    if route == "coder":
        result_gen = run_coder_async(prompt)
    else:
        result_gen = run_analyst_async(prompt)
        
    result_text = ""
    async for chunk in result_gen:
        result_text += chunk

    return {
        "route": route,
        "result": result_text,
        "decision": decision
    }
