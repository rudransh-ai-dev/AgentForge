# Technical Architecture Deep Dive

This document explains the internal engineering of the AI Agent IDE, focusing on the Multi-Agent Orchestration and VRAM Management.

## 1. High-Level Communication Flow
The system follows a **Modular Publisher-Subscriber** pattern via WebSockets:
1. **Frontend (React)**: Sends a prompt + execution mode (`auto`, `direct`, or `agent`).
2. **Backend (FastAPI)**: Receives the prompt and kicks off the `Orchestrator`.
3. **Event Bus**: As each agent works, it emits JSON events (e.g., `START`, `UPDATE`, `COMPLETE`) to the frontend in real-time.
4. **Visualizer (ReactFlow)**: Listens to these events and updates the node status/colors on the canvas.

---

## 2. The VRAM Scheduler (Key Innovation)
One of the most complex parts of the system is managing GPU memory for large models.

### 2.1 The "Heavy" Model Problem
Models like `codestral:22b` or `gpt-oss:20b` take 12-16GB of VRAM. If we load two at once, the system crashes.

### 2.2 The Solution: Exclusive Locking
The `vram_scheduler.py` implements a **FIFO Lock Control**:
- **Co-Residency**: "Light" models (under 9GB) like `llama3.1` and `deepseek-r1` are allowed to stay loaded together.
- **Exclusive Access**: When a "Heavy" model (over 10GB) is requested, the scheduler triggers a `UNLOAD ALL` command to Ollama. It clears the GPU memory, loads the single Heavy model, runs the task, and then unloads it back to make room for the lighter pipeline models.

---

## 3. The 3-Stage Production Pipeline
When running in **Agent Mode**, the orchestrator follows a rigorous 3-stage process to ensure code quality:

### Stage 1: The Writer (Architecting)
The primary code model (e.g., `gpt-oss:20b`) generates the folder structure and raw code logic. It focuses on the "First Draft."

### Stage 2: The Editor (Refinement)
The code is passed to the Editor agent (e.g., `qwen2.5-coder:14b`). Its job is to "lint" the code—fixing syntax errors, refining variable names, and ensuring the code follows the best practices for that specific language.

### Stage 3: The Tester (QA)
The final code is reviewed by the Tester (e.g., `deepseek-r1:8b`). It analyzes the code for potential bugs, security flaws, or edge cases. If it finds a "verdict: FAIL", the code is sent back to the Editor for one automated iteration of fixes.

---

## 4. Prompt Engineering Persistence
To prevent LLM hallucination, the system uses a **Global Prompt Library** in `backend/core/prompts/`. 
- Every agent has a dedicated Markdown prompt file.
- These prompts are loaded via a `SafePromptTemplate` that allows embedding dynamic variables without breaking the LLM's JSON output format.

---

## 5. Persistent Workspace
Unlike most AI chats, this system features a real-world **Workspace Directory**.
- All generated code is saved to `workspace/<project_id>/`.
- The frontend includes a `WorkspaceExplorer` component that allows users to navigate the files and download the entire project as a zip.

---
**Prepared for Academic Review — v4.2**
