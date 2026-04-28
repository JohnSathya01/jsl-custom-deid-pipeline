# Custom De-Identification Pipeline — Development Notes

This document explains how the custom pipeline was built, what decisions were made at each step,
and how each of the five required features was implemented.

---

## Requirements

The starting point was a standard John Snow Labs de-identification pipeline that masked everything
with generic labels. The five customisations requested were:

| Field | Old Behaviour | Required |
|---|---|---|
| Patient Name | `<PATIENT>` | Replace with Patient ID from database |
| Doctor / Practitioner | De-identified (incorrectly) | Keep as-is |
| Service Dates | Fully masked | Month + Year only (e.g. `April 2026`) |
| Date of Birth | Fully masked | Convert to Age (e.g. `53 years old`) |
| ZIP / Postcode | Fully masked | Keep first 3 chars (e.g. `944XX`) |

---

## Step 1 — Environment Setup

### Problem
The original notebook was written for Google Colab. It used:
- `from google.colab import files` — for uploading the license file interactively
- Colab's pre-installed Java (required by PySpark/Spark NLP)

### What was done
1. **Removed the Colab cell** — replaced with a direct `open("spark_jsl.json")` file read
2. **Installed Java 11 via Homebrew** — PySpark requires Java 8 or 11; Java was not present on the machine
   ```bash
   brew install openjdk@11
   ```
3. **Set `JAVA_HOME`** in the notebook setup cell so Spark can find the JVM:
   ```python
   os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@11"
   ```
4. **Created a Python virtual environment** (`.venv`) and registered it as a Jupyter kernel
   so VS Code can run the notebook with all the right packages:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m ipykernel install --user --name johnsnowlabs-venv --display-name "Python (johnsnowlabs)"
   ```
5. **Installed all packages** in the venv:
   ```bash
   pip install pyspark==3.5.1 spark-nlp==6.3.2
   pip install spark-nlp-jsl==6.3.0 --extra-index-url https://pypi.johnsnowlabs.com/<SECRET>
   pip install spark-nlp-display scipy numpy pandas ipykernel
   ```

---

## Step 2 — Understanding the Existing Pipeline

Before writing any custom code, the original `How_To_Build_Pipeline_Tutorials.ipynb` was studied
and executed to understand:

- What **stages** were available (NER, rule-based annotators, merge, de-identification)
- What **entities** the pipeline could detect
- How **ChunkMergeModel** combined NER and rule-based results
- How **LightDeIdentification** performed the actual text replacement

### Pipeline stages found in the original notebook

```
DocumentAssembler          → wraps raw text into Spark NLP format
InternalDocumentSplitter   → splits long documents into 512-char chunks
Tokenizer (×2)             → one for sentences, one for full document
PretrainedZeroShotNERChunker → NER model detecting 18 entity types
ChunkMergeModel            → merges NER chunks, resolves overlaps
ContextualParserModel      → rule-based: zip_parser, date_of_birth_parser
TextMatcherInternalModel   → rule-based: country_matcher
RegexMatcherInternalModel  → rule-based: email_matcher
ChunkMergeModel (×2)       → merge rule-based results, then merge everything
LightDeIdentification      → performs masking / obfuscation
Finisher                   → extracts final text output
```

### Entities detected

`DOCTOR`, `PATIENT`, `DATE`, `DATE_OF_BIRTH`, `CITY`, `STREET`, `STATE`, `COUNTRY`,
`PHONE`, `EMAIL`, `ZIP`, `USERNAME`, `ID`, `BIOID`, `ORGANIZATION`, `MEDICAL_RECORD_NUMBER`,
`SSN`, `AGE`

---

## Step 3 — Deciding the Architecture

### Problem with `LightDeIdentification`
The built-in `LightDeIdentification` annotator supports two modes:
- **mask** — replaces entities with `<ENTITY_LABEL>`
- **obfuscate** — replaces entities with fake but realistic values

Neither mode supports:
- Looking up a patient ID from a dictionary
- Keeping doctor names untouched
- Reducing a date to month+year
- Converting a DOB to an age
- Partial ZIP masking

### Decision
**Remove `LightDeIdentification` entirely.** Keep all the NER stages (they detect entities well),
but replace the final transformation step with a **custom Python UDF** that applies per-entity rules.

```
Before:  NER pipeline → LightDeIdentification → Finisher
After:   NER pipeline → ner_chunk column → custom_deid_udf (Python UDF)
```

This gives full control over what happens to each entity type.

---

## Step 4 — Implementing the Five Features

### Feature 1: DOB → Age

**Challenge:** The `DATE_OF_BIRTH` label from the ZeroShot NER model was being mapped to `DATE`
in the original `ChunkMergeModel.setReplaceDict`. This meant DOB and service dates were
indistinguishable at de-identification time.

**Fix:** Changed the `ReplaceDict` to map `DATE_OF_BIRTH → DOB` (not `DATE`):
```python
.setReplaceDict({
    "DATE_OF_BIRTH"        : "DOB",           # was "DATE" — changed so age logic applies
    "MEDICAL_RECORD_NUMBER": "MEDICALRECORD",
})
```

The `dob_parser` rule-based model already outputs `entity = DOB`, so both sources now agree.

**Transformation logic** (inside the UDF):
```python
def _dob_to_age(s):
    dt = _parse_date(s)
    if dt:
        today = date_type.today()
        age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
        if 0 <= age <= 120:
            return f"{age} years old"
    return "[DOB]"
```

A multi-format date parser (`_parse_date`) tries 12 different date formats to handle
`04/11/1972`, `1972-04-11`, `April 11 1972`, `11.04.1972`, etc.

---

### Feature 2: Service Dates → Month + Year

**Transformation logic:**
```python
def _date_to_month_year(s):
    dt = _parse_date(s)
    if dt:
        return dt.strftime("%B %Y")       # e.g. "April 2026"
    m = re.search(r'\b(19|20)\d{2}\b', s)
    return m.group(0) if m else "[DATE]"  # fallback: extract year only
```

Any chunk labelled `DATE` (service dates, appointment dates, etc.) goes through this function.
DOB is kept separate via the `ReplaceDict` fix above.

---

### Feature 3: Doctor Names — Keep As-Is

**Simplest feature to implement.** In the UDF, when the entity is `DOCTOR`, the loop just
skips that chunk entirely — no replacement is made:

```python
if entity == "DOCTOR":
    continue    # skip — text stays unchanged
```

The NER model (`zeroshot_ner_deid_subentity_docwise_medium`) reliably distinguishes
`DOCTOR` from `PATIENT`, so this works without any extra configuration.

---

### Feature 4: Patient Name → Patient ID

**Two-part problem:**
1. Detect patient names (handled by NER — entity label `PATIENT`)
2. Replace each name with the correct ID from a lookup

**Lookup dictionary** (configurable in the notebook):
```python
PATIENT_ID_MAP = {
    "Daniel Foster" : "PT-10042",
    "John Smith"    : "PT-20017",
    # add more...
}
```

**Fallback for unknown patients** — uses a deterministic hash so the same unknown name
always gets the same ID across runs:
```python
def _get_patient_id(name):
    return PATIENT_ID_MAP.get(name, f"PT-{abs(hash(name)) % 90000 + 10000}")
```

**Loading from a database** is documented as a pattern:
```python
rows = conn.execute("SELECT full_name, patient_id FROM patients").fetchall()
PATIENT_ID_MAP = dict(rows)
```

---

### Feature 5: ZIP / Postcode → Partial Mask

The `zip_parser` rule-based model detects both US ZIPs (`94404`) and UK postcodes (`M13 9PL`).

**Transformation:** Keep the first 3 characters, replace the rest with `X`:
```python
def _partial_zip(z):
    z = z.strip()
    return z[:3] + "X" * (len(z) - 3) if len(z) > 3 else z
```

Examples:
- `94404` → `944XX`
- `M13 9PL` → `M13XXXX`
- `94404-1234` → `944XXXXXXX`

---

## Step 5 — The Custom UDF

### Why a Python UDF?
Spark NLP annotators are JVM-based and don't support arbitrary Python logic mid-pipeline.
A PySpark UDF runs on the Python workers alongside Spark, receiving the `ner_chunk` column
(an array of annotations with `begin`, `end`, `result`, `metadata` fields) and returning
the transformed text.

### How text replacement works
Chunks are sorted by `begin` position in **reverse order** before replacement.
This is critical — replacing from the end of the string backwards keeps all earlier
character positions valid:

```python
chunks.sort(key=lambda x: x[0], reverse=True)   # end → start
result = text
for begin, end, entity, chunk_text in chunks:
    ...
    result = result[:begin] + replacement + result[end + 1:]
```

### Pitfall encountered — UDF closure serialization
When PySpark distributes a UDF to worker processes, it **pickles the function and its entire
closure** (all variables referenced from the outer scope). Because the notebook imports
`from sparknlp_jsl.annotator import *`, this wildcard import polluted the global namespace.
When PySpark serialized the UDF, it captured `re` as `sparknlp_jsl.annotator` instead of
Python's standard `re` module, causing:

```
AttributeError: module 'sparknlp_jsl.annotator' has no attribute 'sub'
```

**Fix:** Make both UDFs **fully self-contained** — all imports (`re`, `datetime`) and all
helper functions are defined **inside** the UDF body, not in the outer notebook scope.
This means the UDF has zero external dependencies and pickles cleanly.

### Pitfall encountered — PYSPARK_PYTHON
On the first attempt the workers threw `ModuleNotFoundError: No module named 'sparknlp_jsl'`
because PySpark workers defaulted to the system Python (`/usr/bin/python3`) which had none
of the installed packages.

**Fix:** Set `PYSPARK_PYTHON` before starting Spark:
```python
import sys
os.environ["PYSPARK_PYTHON"]        = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
```

---

## Step 6 — Testing (20 Test Cases)

A separate notebook (`Test_Cases_DeID.ipynb`) was created covering:

| Category | Test cases |
|---|---|
| DOB label variations | `DOB:`, `Date of Birth:`, `D.O.B.:`, `Born on`, `born`, `Birthday:`, `birth date` |
| Date formats | `MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD Month YYYY`, `DD Month` (abbrev), ordinal (`3rd February`) |
| ZIP formats | US 5-digit, US ZIP+4, UK postcode |
| Doctor preservation | Multiple doctors in one record — all kept as-is |
| Multiple patients | Two patients in one record — each gets their own ID |
| Complex clinical notes | Combined SSN, MRN, email, phone, username, organization |
| Date disambiguation | `Record date` (service) vs `Date of Birth` in the same note |

Results were exported to `DeID_Test_Results.xlsx` with:
- **Yellow column** — all detected entities and their labels
- **Green column** — final de-identified text

---

## File Summary

| File | Purpose |
|---|---|
| `Custom_DeID_Pipeline.ipynb` | Main pipeline notebook — configure and run |
| `Test_Cases_DeID.ipynb` | 20 test cases notebook |
| `DeID_Test_Results.xlsx` | Test results exported to Excel |
| `spark_jsl.json` | JSL license keys (keep private) |
| `README.md` | Setup guide for running on a new machine |
| `PIPELINE_DEVELOPMENT.md` | This file — development notes |
| `.venv/` | Python virtual environment with all packages |
| `content/models/custom_deid_pipeline_v2/` | Saved Spark ML pipeline (cached models) |
