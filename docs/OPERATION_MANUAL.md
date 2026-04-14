# Operation Manual: Using the AI Agent IDE

This guide explains how to interact with the system once it is set up and running.

## 1. Entering the IDE
1. Ensure the backend and frontend are running.
2. Open your browser to `http://localhost:5173`.
3. You will see the **Project Landing Page**. Click **"Launch IDE"** to enter the workspace.

---

## 2. The Agent Canvas
The main interface is the **Agent Canvas**. This is a visual flow representing the thinking process of the AI.

### 2.1 Nodes
- **Input Node**: Where you type your instructions.
- **Manager Node**: Shows the planning and routing phase.
- **Agent Nodes (Writer, Editor, Tester, etc.)**: These light up in colors when the agent is active.
- **Output Node**: Shows the final generated code or project.

---

## 3. Execution Modes
In the top bar, you can select different modes for task processing:

| Mode | Description |
|------|-------------|
| **Auto** | Recommended. The system automatically decides if it needs a single model or the full agent fleet. |
| **Direct** | Fast, single-model response. Best for simple questions. |
| **Agent** | Forced multi-agent pipeline. Best for building complete software projects. |

---

## 4. Special Features

### 4.1 🧠 Deep Think Mode
Toggle the **"Fast / Deep Think"** button in the header. 
- **Fast**: Uses optimized 8B-14B models for speed.
- **Deep Think**: Forces the system to use the heavy-duty **Codestral 22B** model for architecture and complex drafting.

### 4.2 🔍 Researcher Mode
You don't need to click anything for this. If you ask a question like *"Explain quantum computing"* or *"Compare React vs Vue"*, the system's **Smart Router** will automatically send the task to the **Researcher agent**.

---

## 5. Working with Code (Workspace)
Once a project is generated:
1. It is automatically saved to the `workspace/` folder on your hard drive.
2. You can view the files in the **Workspace Explorer** on the left side of the screen.
3. You can click on any file to view its contents or use the **"Run"** icon (if configured) to execute the code in the local sandbox.

---

## 6. Troubleshooting
- **Frontend not loading**: Check if the backend is running (`python main.py`).
- **Models not responding**: Ensure Ollama is running and you have "pulled" the models listed in the Requirements guide.
- **Latency**: Large models (like gpt-oss) may take 10-20 seconds to load into VRAM the first time.
