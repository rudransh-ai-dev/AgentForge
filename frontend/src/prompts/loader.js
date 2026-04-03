/**
 * Shared prompt loader — reads from /prompts/ at project root.
 * Each agent file has "## Pipeline Prompt" and "## Chat Prompt" sections.
 */

const PROMPTS = {
  manager: { pipeline: "", chat: "" },
  coder: { pipeline: "", chat: "" },
  analyst: { pipeline: "", chat: "" },
  critic: { pipeline: "", chat: "" },
};

let loaded = false;

async function loadPrompts() {
  if (loaded) return PROMPTS;
  const agents = ["manager", "coder", "analyst", "critic"];
  await Promise.all(
    agents.map(async (agent) => {
      try {
        const res = await fetch(`/prompts/${agent}.md`);
        if (!res.ok) return;
        const text = await res.text();
        const parts = text.split(`## ${agent === "manager" ? "Manager" : agent.charAt(0).toUpperCase() + agent.slice(1)} `);
        // Fallback: split by section markers
        const pipelineMatch = text.match(/## Pipeline Prompt\n([\s\S]*?)(?=## Chat Prompt|$)/);
        const chatMatch = text.match(/## Chat Prompt\n([\s\S]*)/);
        if (pipelineMatch) PROMPTS[agent].pipeline = pipelineMatch[1].trim();
        if (chatMatch) PROMPTS[agent].chat = chatMatch[1].trim();
      } catch {
        // Use defaults from agents.js
      }
    })
  );
  loaded = true;
  return PROMPTS;
}

export { PROMPTS, loadPrompts };
