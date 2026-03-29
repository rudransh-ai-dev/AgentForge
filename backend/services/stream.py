import time

def stream_events(prompt, route):
    yield f"Manager analyzing task...\n"
    time.sleep(0.5)

    yield f"Routing to {route} agent...\n"
    time.sleep(0.5)

    yield f"Executing...\n"
