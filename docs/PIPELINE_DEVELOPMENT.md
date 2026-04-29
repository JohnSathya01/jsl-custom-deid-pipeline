# De-Identification Pipeline — Technical Development Notes

Documents the architecture decisions, implementation details, and pitfalls encountered
across both pipelines.

---

## Requirements

| Field | Old Behaviour | Required |
|---|---|---|
| Patient Name | `<PATIENT>` | Replace with Patient ID from database |
| Doctor / Practitioner | De-identified (incorrectly) | Keep as-is |
| Service Dates | Fully masked | Month + Year only (e.g. `August 2012`) |
| Date of Birth | Fully masked | Convert to Age (e.g. `78 years old`) |
| ZIP / Postcode | Fully masked | Keep first 3 chars (e.g. `970XX`) |

---

## Environment Setup

### Migrating from Google Colab to local

The original tutorial notebook used:
- `from google.colab import files` — removed; replaced with `open("spark_jsl.json")`
- Colab's pre-installed Java — installed via `brew install openjdk@11`
- `JAVA_HOME` must be set before Spark starts:
  ```python
  os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@11"
  ```

### Virtual environment and kernel registration

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyspark==3.5.1 spark-nlp==6.3.2
pip install spark-nlp-jsl==6.3.0 --extra-index-url https://pypi.johnsnowlabs.com/<SECRET>
pip install spark-nlp-display scipy numpy pandas openpyxl ipykernel nbclient nbformat
.venv/bin/python -m ipykernel install --user --name johnsnowlabs-venv --display-name "Python (johnsnowlabs)"
```

---

## Pipeline 1 — Plain Text (`Custom_DeID_Pipeline.ipynb`)

### Architecture decision — remove LightDeIdentification

The built-in `LightDeIdentification` annotator supports only two modes:
- `mask` — replaces with `<ENTITY_LABEL>`
- `obfuscate` — replaces with fake but realistic values

Neither supports patient ID lookup, keeping doctors, age calculation, or partial ZIP masking.

**Decision:** Remove `LightDeIdentification` entirely. Keep all NER stages; replace the final
transformation with a custom Python UDF.

```
Before:  NER pipeline → LightDeIdentification → Finisher
After:   NER pipeline → ner_chunk column → custom_deid_udf (Python UDF)
```

### Pipeline stages

```
DocumentAssembler
InternalDocumentSplitter    (512-char chunks, 50-char overlap)
Tokenizer (sentence)
Tokenizer (document)
PretrainedZeroShotNERChunker  ← detects 18 entity types
ChunkMergeModel (NER)         ← ReplaceDict: DATE_OF_BIRTH→DOB, MEDICALRECORD→MEDICALRECORD
ContextualParserModel         zip_parser
ContextualParserModel         date_of_birth_parser
RegexMatcherInternalModel     email_matcher
TextMatcherInternalModel      country_matcher
ChunkMergeModel (rules)       ← merge rule-based results
ChunkMergeModel (final)       ← merge NER + rules, DiverseLonger strategy
custom_deid_udf               ← Python UDF applying per-entity logic
```

### Feature implementations

#### DOB → Age

The `DATE_OF_BIRTH` label from ZeroShot NER was originally mapped to `DATE` in `setReplaceDict`,
making DOB and service dates indistinguishable. Fixed by mapping to `DOB` instead:

```python
.setReplaceDict({
    "DATE_OF_BIRTH"        : "DOB",           # was "DATE"
    "MEDICAL_RECORD_NUMBER": "MEDICALRECORD",
})
```

Age calculation:
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

`_parse_date` tries 12 formats: `MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD Month YYYY`, etc.

#### Service Dates → Month + Year

```python
def _date_to_month_year(s):
    dt = _parse_date(s)
    if dt: return dt.strftime("%B %Y")
    m = re.search(r'\b(19|20)\d{2}\b', s)
    return m.group(0) if m else "[DATE]"   # fallback: year only
```

#### Doctor Names — Keep As-Is

```python
if entity == "DOCTOR":
    continue    # skip chunk entirely
```

#### Patient Name → Patient ID

```python
PATIENT_ID_MAP = {"Myra Jones": "PT-00001", ...}

def _get_patient_id(name):
    return PATIENT_ID_MAP.get(name, f"PT-{abs(hash(name)) % 90000 + 10000}")
```

Deterministic hash ensures the same unknown name always receives the same ID across runs.

Database pattern:
```python
rows = conn.execute("SELECT full_name, patient_id FROM patients").fetchall()
PATIENT_ID_MAP = dict(rows)
```

#### ZIP → Partial Mask

```python
def _partial_zip(z):
    z = z.strip()
    return z[:3] + "X" * (len(z) - 3) if len(z) > 3 else z
# 94404 → 944XX  |  M13 9PL → M13XXXX  |  94404-1234 → 944XXXXXXX
```

### Custom UDF design

Replacements are applied **end → start** to keep character positions valid after each substitution:

```python
chunks.sort(key=lambda x: x[0], reverse=True)
result = text
for begin, end, entity, chunk_text in chunks:
    result = result[:begin] + replacement + result[end + 1:]
```

---

## Pipeline 2 — XML (`XML_DeID_Pipeline.ipynb`)

### Architecture — two-pass hybrid

```
XML in
  │
  ├─ Pass 1: xml.etree.ElementTree structural rules
  │          Targets known PHI by tag name / attribute pattern.
  │          No NLP needed — the tag tells us what the data is.
  │
  └─ Pass 2: Full JSL ZeroShot NER on all text nodes
             Walks root.iter(), collects every element.text and element.tail,
             runs NLP pipeline, writes back.
             Works on any XML schema — no tag-name assumptions.
```

### Pass 1 — Structural rules

| Tag / Attribute | PHI type | Transformation |
|---|---|---|
| `patient/name/given` + `family` | PATIENT | → Patient ID |
| `assignedPerson/name` | DOCTOR | kept as-is |
| `relatedPerson/name`, `associatedPerson/name`, `informationRecipient/name` | RELATED | → `[RELATED_PERSON]` |
| `birthTime/@value` (YYYYMMDD) | DOB | → `yyyymmdd_to_age()` |
| `id[@root="2.16.840.1.113883.4.1"]/@extension` | SSN | → `[SSN]` |
| `effectiveTime/@value`, `low/@value`, `high/@value` (YYYYMMDD) | SERVICE_DATE | → `yyyymmdd_to_month_year()` |
| `postalCode` text | ZIP | → partial mask |
| `telecom[@value starts with "tel:"]` | PHONE | → `tel:[PHONE]` |
| `streetAddressLine` text | STREET | → `[STREET]` |

Namespace is derived dynamically from the root tag so the same code works across CDA schemas:
```python
_ns_match = re.match(r'\{(.+?)\}', root.tag)
NS = _ns_match.group(1) if _ns_match else ""
def t(name): return f"{{{NS}}}{name}" if NS else name
```

### Pass 2 — ZeroShot NER on text nodes

```python
# Collect every text/tail node regardless of tag name
text_nodes = []
for el in root.iter():
    if el.text and el.text.strip():
        text_nodes.append((el, "text", el.text))
    if el.tail and el.tail.strip():
        text_nodes.append((el, "tail", el.tail))

# Deduplicate, run NLP once per unique string
unique_texts = list({txt for _, _, txt in text_nodes})
df = spark.createDataFrame(enumerate(unique_texts), ["idx", "text"])
result_df = nlp_model.transform(df).withColumn("deid_text", custom_deid_udf(...))

# Build lookup and write back
deid_map = {row["text"]: row["deid_text"] for row in result_df.collect()
            if row["text"] != row["deid_text"]}
for el, attr, orig in text_nodes:
    deid = deid_map.get(orig)
    if deid:
        setattr(el, attr, deid)  # el.text = deid  or  el.tail = deid
```

Deduplication ensures each unique string is processed only once through Spark NLP,
reducing compute time when the same phrase appears in multiple table cells.

---

## Pitfalls and Fixes

### 1 — Wildcard import namespace pollution

`from sparknlp_jsl.annotator import *` overwrites `re` in the notebook global namespace.
This caused two separate failures:

**In the UDF** (both pipelines):
```
AttributeError: module 'sparknlp_jsl.annotator' has no attribute 'sub'
```
PySpark pickles the UDF and its entire closure. Because `re` resolved to
`sparknlp_jsl.annotator`, the serialized UDF had the wrong module.

**Fix:** All imports and helpers defined *inside* the UDF body — zero external closure dependencies.

**In notebook cells after the wildcard import** (XML pipeline):
```
AttributeError: module 'sparknlp_jsl.annotator' has no attribute 'match'
```
**Fix:** Re-import standard library modules explicitly *after* the wildcard:
```python
from sparknlp_jsl.annotator import *
import re, copy, json, os, sys                 # ← restore after wildcard
from datetime import datetime, date as date_type
```

---

### 2 — PYSPARK_PYTHON defaulting to system Python

Workers threw `ModuleNotFoundError: No module named 'sparknlp_jsl'` because PySpark
defaulted to `/usr/bin/python3` which had none of the venv packages.

**Fix:**
```python
import sys
os.environ["PYSPARK_PYTHON"]        = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
```

---

### 3 — JSL floating license lock

`JslInvalidLicenseException: Cannot check-in the license or license already in use.`

JSL uses a `LockManager` that holds a lease per active Spark session. If a notebook
crashes before Spark stops cleanly, the lease is not released and the next session
cannot acquire it.

**Fix — at session start:** stop any existing session before starting a new one:
```python
from pyspark.sql import SparkSession
existing = SparkSession.getActiveSession()
if existing:
    existing.stop()
    import time; time.sleep(3)   # give license server time to release
```

**Fix — at session end:** always stop Spark explicitly so the lock is released:
```python
spark.stop()
```

---

### 4 — DOB / DATE label ambiguity

`DATE_OF_BIRTH` from the ZeroShot NER model was remapped to `DATE` by the default
`ChunkMergeModel.setReplaceDict`, making DOB and service dates indistinguishable
at the replacement stage.

**Fix:** Map `DATE_OF_BIRTH → DOB` so the UDF can apply age logic specifically:
```python
.setReplaceDict({"DATE_OF_BIRTH": "DOB", "MEDICAL_RECORD_NUMBER": "MEDICALRECORD"})
```

---

### 5 — YYYYMMDD dates in XML narrative table cells

Service dates stored as `20120806` inside `<td>` elements were not caught by
Pass 1 (which targets attributes, not table cell text content) and were not caught
by Pass 2's text-format date regex.

**Fix:** Pass 2 NLP handles these via the ZeroShot model. Additionally, a YYYYMMDD
regex was added as a fallback:
```python
_YYYYMMDD_RE = re.compile(r'\b((?:19|20)\d{6})\b')
def _replace_yyyymmdd(m):
    dt = datetime.strptime(m.group(1), '%Y%m%d')
    return dt.strftime('%B %Y')
```

---

## Testing

`Test_Cases_DeID.ipynb` — 20 test cases across:

| Category | Coverage |
|---|---|
| DOB label variations | `DOB:`, `Date of Birth:`, `D.O.B.:`, `Born on`, `born`, `Birthday:`, `birth date` |
| Date formats | `MM/DD/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD Month YYYY`, ordinal (`3rd February`) |
| ZIP formats | US 5-digit, US ZIP+4, UK postcode |
| Doctor preservation | Multiple doctors in one record |
| Multiple patients | Two patients, each mapped to their own ID |
| Complex clinical notes | SSN + MRN + email + phone + username + org in one record |
| Date disambiguation | `Record date` (service) vs `Date of Birth` in the same note |

Output: `outputs/DeID_Test_Results.xlsx` — yellow = detected entities, green = de-identified text.

XML pipeline tested against `file9.txt` (HL7 CDA, 119 KB):
- 132 changes from Pass 1 (structural rules)
- 97 text nodes updated from Pass 2 (ZeroShot NER)
- 241 total changes logged in `outputs/XML_DeID_Results.xlsx`

---

## File Reference

| File | Purpose |
|---|---|
| `notebooks/Custom_DeID_Pipeline.ipynb` | Plain text pipeline — main notebook |
| `notebooks/Test_Cases_DeID.ipynb` | 20 test cases |
| `notebooks/XML_DeID_Pipeline.ipynb` | XML / HL7 CDA pipeline |
| `run_notebook.py` | Headless runner — accepts notebook name as CLI argument |
| `outputs/DeID_Test_Results.xlsx` | Plain text test results |
| `outputs/XML_DeID_Results.xlsx` | XML de-ID audit log |
| `outputs/file9_deid.xml` | De-identified CDA sample |
| `docs/HOW_IT_WORKS.md` | Plain-language explanation |
| `docs/PIPELINE_DEVELOPMENT.md` | This file |
| `spark_jsl.json` | JSL license keys — never committed, listed in `.gitignore` |
| `.venv/` | Python virtual environment — never committed |
| `content/models/` | Cached Spark ML models — never committed |
