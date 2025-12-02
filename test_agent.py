import sys
import subprocess
from pathlib import Path

# Change to the level3agent directory
agent_dir = Path(__file__).parent / "level3agent"
sys.path.insert(0, str(agent_dir.parent))

# Run the agent with input
process = subprocess.Popen(
    [sys.executable, str(agent_dir / "agent.py")],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=str(agent_dir.parent)
)

# Send the question and exit command
input_text = "How does RAG reduce hallucinations?\nexit\n"
stdout, _ = process.communicate(input=input_text, timeout=120)

print(stdout)









