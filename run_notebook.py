import asyncio
import os
import nbformat
from nbclient import NotebookClient

# Ensure JAVA_HOME is set for the kernel environment
os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@11"
os.environ["PATH"] = "/opt/homebrew/opt/openjdk@11/bin:" + os.environ.get("PATH", "")

with open("XML_DeID_Pipeline.ipynb") as f:
    nb = nbformat.read(f, as_version=4)

client = NotebookClient(
    nb,
    timeout=-1,
    kernel_name="johnsnowlabs-venv",
    resources={"metadata": {"path": "/Users/John.Sathya/johnsnowlabs"}},
)

asyncio.run(client.async_execute())

with open("XML_DeID_Pipeline_output.ipynb", "w") as f:
    nbformat.write(nb, f)

print("Notebook executed successfully!")
