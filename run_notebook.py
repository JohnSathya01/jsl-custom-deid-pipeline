"""
Run any pipeline notebook headlessly from the command line.

Usage:
    python run_notebook.py                          # runs XML_DeID_Pipeline (default)
    python run_notebook.py Custom_DeID_Pipeline
    python run_notebook.py Test_Cases_DeID
    python run_notebook.py XML_DeID_Pipeline
"""
import asyncio, os, sys
import nbformat
from nbclient import NotebookClient

os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@11"
os.environ["PATH"]      = "/opt/homebrew/opt/openjdk@11/bin:" + os.environ.get("PATH", "")

NOTEBOOK_DIR = os.path.join(os.path.dirname(__file__), "notebooks")
PROJECT_DIR  = os.path.dirname(__file__)

name = sys.argv[1] if len(sys.argv) > 1 else "XML_DeID_Pipeline"
inp  = os.path.join(NOTEBOOK_DIR, f"{name}.ipynb")
out  = os.path.join(PROJECT_DIR,  f"{name}_output.ipynb")

print(f"Running: {inp}")
with open(inp) as f:
    nb = nbformat.read(f, as_version=4)

client = NotebookClient(
    nb,
    timeout=-1,
    kernel_name="johnsnowlabs-venv",
    resources={"metadata": {"path": PROJECT_DIR}},
)

asyncio.run(client.async_execute())

with open(out, "w") as f:
    nbformat.write(nb, f)

print(f"Done. Output saved to: {out}")
