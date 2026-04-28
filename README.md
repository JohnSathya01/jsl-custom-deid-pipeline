# Custom De-Identification Pipeline — Setup Guide

## What it does

| Field | Output |
|---|---|
| **Patient Name** | Replaced with Patient ID (e.g. `PT-10042`) |
| **Doctor / Practitioner Name** | Kept as-is |
| **Service Dates** | Reduced to Month + Year (e.g. `March 2024`) |
| **Date of Birth** | Converted to Age (e.g. `54 years old`) |
| **ZIP / Postcode** | First 3 chars kept (e.g. `944XX`, `M13XXXX`) |
| **Everything else** | Masked with label (e.g. `[PHONE]`, `[EMAIL]`) |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9+ |
| Java | 11 (required for Spark) |
| John Snow Labs license | `spark_jsl.json` file |

---

## Step 1 — Install Java 11

### macOS
```bash
brew install openjdk@11
sudo ln -sfn /opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-11.jdk
```

### Ubuntu / Debian
```bash
sudo apt update && sudo apt install -y openjdk-11-jdk
```

### Windows
Download and install from: https://adoptium.net/temurin/releases/?version=11

Verify:
```bash
java -version
# Should show: openjdk version "11.x.x"
```

---

## Step 2 — Clone / Copy the project

Copy the project folder to the new machine. The folder should contain:
```
johnsnowlabs/
├── Custom_DeID_Pipeline.ipynb   ← main notebook
├── spark_jsl.json               ← your license file (copy from original machine)
└── README.md                    ← this file
```

> **Important:** `spark_jsl.json` contains your JSL license keys. Copy it from your original machine or download a fresh one from your John Snow Labs account.

---

## Step 3 — Create a virtual environment

```bash
cd johnsnowlabs
python3 -m venv .venv
```

---

## Step 4 — Install dependencies

```bash
# Activate the environment
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install Spark NLP (open source)
pip install pyspark==3.5.1 spark-nlp==6.3.2

# Install Spark NLP Healthcare (requires license)
# Get your SECRET from spark_jsl.json
SECRET=$(python3 -c "import json; print(json.load(open('spark_jsl.json'))['SECRET'])")
pip install spark-nlp-jsl==6.3.0 --extra-index-url https://pypi.johnsnowlabs.com/$SECRET

# Install display + notebook dependencies
pip install spark-nlp-display scipy numpy pandas ipykernel nbconvert nbclient
```

---

## Step 5 — Register the Jupyter kernel

```bash
python -m ipykernel install --user --name jsl-venv --display-name "Python (johnsnowlabs)"
```

---

## Step 6 — Run the notebook

### Option A — VS Code (recommended)
1. Open `Custom_DeID_Pipeline.ipynb` in VS Code
2. Click the kernel picker (top right) → select **"Python (johnsnowlabs)"**
3. **Run All Cells** (`Shift+Cmd+Enter` on Mac / `Shift+Ctrl+Enter` on Windows)

### Option B — JupyterLab / Classic Jupyter
```bash
source .venv/bin/activate
pip install jupyterlab
jupyter lab Custom_DeID_Pipeline.ipynb
```
Then select **"Python (johnsnowlabs)"** kernel and run all cells.

### Option C — Command line (headless)
```bash
source .venv/bin/activate
export JAVA_HOME=/opt/homebrew/opt/openjdk@11     # macOS
# export JAVA_HOME=/usr/lib/jvm/java-11-openjdk   # Linux

python - <<'EOF'
import asyncio, os, nbformat
from nbclient import NotebookClient

os.environ["JAVA_HOME"] = os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-11-openjdk")

with open("Custom_DeID_Pipeline.ipynb") as f:
    nb = nbformat.read(f, as_version=4)

client = NotebookClient(nb, timeout=-1, kernel_name="jsl-venv",
                        resources={"metadata": {"path": "."}})
asyncio.run(client.async_execute())

with open("Custom_DeID_Pipeline_output.ipynb", "w") as f:
    nbformat.write(nb, f)

print("Done! Output saved to Custom_DeID_Pipeline_output.ipynb")
EOF
```

> **Note:** The first run downloads ~700 MB of NLP models. This is one-time only — subsequent runs use the local cache and are much faster.

---

## Customising the Patient ID lookup

Open `Custom_DeID_Pipeline.ipynb` and edit the `PATIENT_ID_MAP` cell:

```python
PATIENT_ID_MAP = {
    "Daniel Foster" : "PT-10042",
    "Laura Foster"  : "PT-10043",
    # Add your patients here:
    "Jane Doe"      : "PT-99001",
}
```

To load from a database instead:
```python
import psycopg2  # or your DB driver
conn = psycopg2.connect(host="...", dbname="...", user="...", password="...")
rows = conn.execute("SELECT full_name, patient_id FROM patients").fetchall()
PATIENT_ID_MAP = dict(rows)
```

---

## JAVA_HOME reference

| OS | Path |
|---|---|
| macOS (Homebrew) | `/opt/homebrew/opt/openjdk@11` |
| Ubuntu/Debian | `/usr/lib/jvm/java-11-openjdk-amd64` |
| Windows | `C:\Program Files\Eclipse Adoptium\jdk-11.x.x.x-hotspot` |

The notebook sets `JAVA_HOME` automatically for macOS Homebrew. If you're on Linux or Windows, update this line in the **Setup** cell:

```python
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"  # Linux example
```
