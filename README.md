# JSL Custom De-Identification Pipeline

A custom clinical text de-identification pipeline built on [John Snow Labs Spark NLP for Healthcare](https://www.johnsnowlabs.com/), supporting both plain text and HL7 CDA XML documents.

---

## What It Does

Medical records contain sensitive personal information (PHI) that must be removed before sharing for research, audits, or transfers. This pipeline automatically detects and replaces that information following five specific rules:

| PHI Type | Example Input | Example Output |
|---|---|---|
| Patient Name | *Myra Jones* | `PT-00001` (mapped from lookup) |
| Doctor Name | *Dr. Henry Seven* | kept as-is |
| Service Date | *08/06/2012* | `August 2012` |
| Date of Birth | *01/05/1947* | `78 years old` |
| ZIP / Postcode | *97006* | `970XX` |

Everything else (SSN, phone, email, address) is replaced with a placeholder: `[SSN]`, `[PHONE]`, `[STREET]`, etc.

---

## Repository Structure

```
jsl-custom-deid-pipeline/
│
├── notebooks/
│   ├── Custom_DeID_Pipeline.ipynb   # Main pipeline — plain text de-identification
│   ├── Test_Cases_DeID.ipynb        # 20 test cases with Excel output
│   └── XML_DeID_Pipeline.ipynb      # HL7 CDA XML de-identification
│
├── outputs/
│   ├── DeID_Test_Results.xlsx       # Test case results (colour-coded)
│   ├── XML_DeID_Results.xlsx        # XML de-ID audit log (145 changes)
│   └── file9_deid.xml               # De-identified sample CDA document
│
├── docs/
│   ├── HOW_IT_WORKS.md              # Plain-language explanation (non-technical)
│   └── PIPELINE_DEVELOPMENT.md      # Technical development notes and decisions
│
├── run_notebook.py                  # Headless notebook runner (command line)
├── .gitignore
└── README.md
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9+ |
| Java | 11 (required by PySpark) |
| JSL License | `spark_jsl.json` at project root |

---

## Setup

### 1. Install Java 11

**macOS**
```bash
brew install openjdk@11
```

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install -y openjdk-11-jdk
```

**Windows** — download from [adoptium.net](https://adoptium.net/temurin/releases/?version=11)

Verify:
```bash
java -version   # should show openjdk 11.x.x
```

### 2. Clone the Repository

```bash
git clone https://github.com/JohnSathya01/jsl-custom-deid-pipeline.git
cd jsl-custom-deid-pipeline
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 4. Install Dependencies

```bash
pip install pyspark==3.5.1 spark-nlp==6.3.2

# Replace <YOUR_SECRET> with the value from your spark_jsl.json
pip install spark-nlp-jsl==6.3.0 --extra-index-url https://pypi.johnsnowlabs.com/<YOUR_SECRET>

pip install spark-nlp-display scipy numpy pandas openpyxl ipykernel nbclient nbformat
```

### 5. Register the Jupyter Kernel

```bash
python -m ipykernel install --user \
    --name johnsnowlabs-venv \
    --display-name "Python (johnsnowlabs)"
```

### 6. Add Your License File

Place your JSL license at the project root as `spark_jsl.json`:

```json
{
  "SECRET": "...",
  "SPARK_NLP_LICENSE": "...",
  "AWS_ACCESS_KEY_ID": "...",
  "AWS_SECRET_ACCESS_KEY": "..."
}
```

> `spark_jsl.json` is in `.gitignore` — it will never be committed to the repository.

---

## How to Run

### Option A — VS Code / JupyterLab

1. Open any notebook from the `notebooks/` folder
2. Select the **Python (johnsnowlabs)** kernel
3. Run All Cells

### Option B — Command Line (headless)

```bash
# Run the XML de-identification pipeline (default)
python run_notebook.py XML_DeID_Pipeline

# Run the plain-text pipeline
python run_notebook.py Custom_DeID_Pipeline

# Run the 20 test cases
python run_notebook.py Test_Cases_DeID
```

Output notebooks are saved to the project root as `<name>_output.ipynb`.

> **Note:** The first run downloads ~700 MB of NLP models. Subsequent runs use the local cache and are much faster.

---

## Pipeline Architecture

```
Plain text input
       │
       ├─ ZeroShot NER model ─────┐
       ├─ zip_parser              ├──► ChunkMerge ──► Custom Rules ──► De-identified text
       ├─ date_of_birth_parser    │
       ├─ email_matcher ──────────┘
       └─ country_matcher

HL7 CDA XML input
       │
       ├─ Stage 1: XML structural rules  (direct tag/attribute targeting)
       └─ Stage 2: Regex rules on narrative <text> sections
```

**NER Model:** `zeroshot_ner_deid_subentity_docwise_medium`
Detects 18 entity types: PATIENT, DOCTOR, DATE, DATE_OF_BIRTH, ZIP, SSN, PHONE, EMAIL, CITY, STREET, STATE, COUNTRY, USERNAME, ID, BIOID, ORGANIZATION, MEDICAL_RECORD_NUMBER, AGE

---

## Customising the Patient Lookup

In `notebooks/Custom_DeID_Pipeline.ipynb`, edit the `PATIENT_ID_MAP` cell:

```python
PATIENT_ID_MAP = {
    "Myra Jones"    : "PT-00001",
    "Daniel Foster" : "PT-10042",
    # Add your patients here
}
```

To load from a database:
```python
rows = conn.execute("SELECT full_name, patient_id FROM patients").fetchall()
PATIENT_ID_MAP = dict(rows)
```

---

## JAVA_HOME Reference

| OS | Path |
|---|---|
| macOS (Homebrew) | `/opt/homebrew/opt/openjdk@11` |
| Ubuntu / Debian | `/usr/lib/jvm/java-11-openjdk-amd64` |
| Windows | `C:\Program Files\Eclipse Adoptium\jdk-11.x.x.x-hotspot` |

If you are on Linux or Windows, update the `JAVA_HOME` line in the setup cell of each notebook.

---

## Documentation

- [HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) — Plain-language explanation (no coding knowledge needed)
- [PIPELINE_DEVELOPMENT.md](docs/PIPELINE_DEVELOPMENT.md) — Technical notes: architecture decisions, pitfalls, and how each feature was built
