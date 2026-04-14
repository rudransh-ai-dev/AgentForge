# Canvas Guide — How to Use the Agent Pipeline Canvas

## What the Canvas Is

The Canvas is a **visual AI pipeline builder** — similar to n8n or ComfyUI but for multi-agent AI workflows.
Each node on the canvas is a **live AI agent**. When you run a task, you can watch each agent activate, process, and hand off to the next one in real time.

---

## Default Pipeline Flow

```
User Input → Manager → Coder / Analyst / Critic → Tool → Executor
```

| Node | Role | Default Model |
|------|------|---------------|
| **User Input** | Entry point — your task enters here | — |
| **Manager** | Reads the task, decides which agent handles it | qwen2.5:14b |
| **Coder** | Writes code, scripts, programs | deepseek-coder-v2:16b |
| **Analyst** | Explains, summarizes, reasons | qwen2.5:14b |
| **Critic** | Reviews code, finds bugs, validates quality | devstral:24b |
| **Tool** | Parses and saves code files to workspace | — |
| **Executor** | Runs the saved code, auto-fixes errors | sandbox |

---

## How to Run a Task

1. Type your task in the **top command bar** (Ctrl+K to focus)
2. Choose execution mode:
   - **auto** — system decides (best for most tasks)
   - **agent** — always use full pipeline (Manager → agents)
   - **direct** — skip pipeline, single model response
3. Press **Enter** — watch nodes light up in sequence

> Tasks that involve writing code, building projects, or fixing bugs automatically use the full pipeline.
> Questions and simple lookups use direct mode.

---

## What Each Node Shows

When a node is active:
- **Blue pulse** = running (agent is generating)
- **Green** = done (agent completed successfully)
- **Red** = error (something failed)

Each node card shows:
- Current status
- Live output preview (first 300 chars)
- Latency in ms
- Token count

---

## Changing an Agent's Model (Live)

You can change the model for any node **without restarting anything**:

1. Hover over a node → the action buttons appear in the top-right corner
2. Click **⚙️ (Settings2 icon)**
3. Change the **Model** dropdown to any available Ollama model
4. Click **Apply**

The next run will use the model you selected for that agent.

Examples:
- Change Coder from `deepseek-coder-v2:16b` to `qwen2.5-coder:14b` for faster responses
- Change Manager to `llama3.1:8b` to save VRAM on simple tasks
- Change Critic to `phi4:latest` for lighter validation

---

## Overriding the System Prompt

Each node has a system prompt that defines its personality and instructions:

1. Hover over a node → click **⚙️**
2. Edit the **System Prompt** field
3. Click **Apply**

Example — make your Coder always add type hints:
```
You are an expert Python engineer. Always add type hints to every function.
Write clean, well-commented code. Never use global variables.
```

---

## Adding Nodes (Drag and Drop)

The **left sidebar** has draggable node types:

| Node Type | Use |
|-----------|-----|
| User Input | Second entry point for branching |
| LLM Agent | Generic agent — set any model + system prompt |
| Coder | Pre-configured for code generation |
| Tool Node | For script execution or API calls |
| Analyst | Pre-configured for analysis tasks |

**Your custom agents** (created in the Agents tab) also appear here.

**To add a node:**
1. Drag any node type from the left sidebar
2. Drop it anywhere on the canvas

**To connect nodes:**
1. Hover over any node — small dots appear on left/right edges
2. Drag from the **right dot** of one node to the **left dot** of another
3. A glowing edge appears

**To delete a node:**
- Hover over it → click the **🗑️ trash icon**
- OR select it and press **Delete / Backspace**

---

## Adding Custom Agents

1. Go to the **Agents tab** (sidebar)
2. Click **New Agent**
3. Fill in:
   - **Name** — what shows on the canvas node
   - **Model** — which Ollama model to use
   - **System Prompt** — the agent's personality and instructions
4. Save

Your custom agent now appears in:
- Canvas sidebar → "Your Agents" section (drag to canvas)
- Agent Chat dropdown (chat with it directly)

---

## Sequential Execution (One Agent at a Time)

The pipeline uses a **global lock** — only one agent generates at a time. This is intentional:
- Prevents VRAM overflow from concurrent models
- Ensures each agent has full context from the previous one
- Makes the visual flow easy to follow

Order: Manager finishes → goes silent → Coder activates → finishes → Critic activates

---

## Canvas Modes vs Execution Modes

| Mode | Canvas active? | Pipeline runs? |
|------|---------------|----------------|
| **agent** | Yes — all nodes light up | Full Manager → agents |
| **direct** | Only the single agent node lights up | No manager, no critic |
| **auto** | Depends on task complexity | System decides |

---

## Timeline Panel (Right Side)

The panel on the right of the canvas shows:

**During a run:** Live event stream
- `start` → agent began (yellow ⚡)
- `update` → streaming output (blue)
- `complete` → agent finished (green ✓)
- `error` → something failed (red ✗)

**Between runs:** Run History
- Last 10 completed runs
- Click any run to expand per-step details
- Shows agent name, output preview, latency per step

---

## Tips for Demo / Interviews

1. **Type a coding task** with "agent" mode selected — every node lights up in sequence
2. **Show the Timeline** panel while it runs — live events look impressive
3. **Change the Coder model mid-session** to show live configurability
4. **Drag a custom agent** onto the canvas to show extensibility
5. **Fullscreen the canvas** (top-right icon) for presentation
