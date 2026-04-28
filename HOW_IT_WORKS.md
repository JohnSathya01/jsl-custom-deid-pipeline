# How the Custom De-Identification Pipeline Works

This document explains the pipeline in plain language — no coding experience needed.

---

## What Problem Does It Solve?

Medical records contain sensitive personal information: patient names, dates of birth,
social security numbers, addresses, phone numbers, and so on.

Before sharing these records (for research, audits, or transfers), that information must
be **removed or replaced** so no one can identify the patient. This process is called
**de-identification**.

The challenge is doing it automatically across thousands of records, while following
specific rules — for example, keeping the doctor's name visible but replacing the
patient's name with an ID number.

---

## The Five Rules We Implemented

| What was found | What happens to it |
|---|---|
| **Patient name** (e.g. *Myra Jones*) | Replaced with a Patient ID (e.g. *PT-00001*) |
| **Doctor name** (e.g. *Dr. Henry Seven*) | Left exactly as-is — not changed |
| **Service dates** (e.g. *08/06/2012*) | Shortened to month and year only (e.g. *August 2012*) |
| **Date of birth** (e.g. *01/05/1947*) | Converted to the patient's current age (e.g. *78 years old*) |
| **ZIP / postcode** (e.g. *97006*) | First 3 digits kept, rest replaced with X (e.g. *970XX*) |

Everything else — SSN, phone number, email, street address — is replaced with a
placeholder like `[SSN]`, `[PHONE]`, or `[STREET]`.

---

## How the Pipeline Reads a Document

Think of the pipeline as an assembly line with two checkpoints:

```
Raw document
     │
     ▼
┌──────────────────────────────────┐
│  CHECKPOINT 1 — "Find the PHI"   │
│                                  │
│  Two types of detectors run:     │
│  • AI model (reads context)      │
│  • Rule-based scanner (patterns) │
└──────────────┬───────────────────┘
               │  List of detected names, dates, ZIPs, etc.
               ▼
┌──────────────────────────────────┐
│  CHECKPOINT 2 — "Replace it"     │
│                                  │
│  Each detected item goes through │
│  the five rules above            │
└──────────────┬───────────────────┘
               │
               ▼
     De-identified document
```

---

## Checkpoint 1 — Finding the PHI

### The AI Model

The first detector is an **AI language model** made by John Snow Labs called
`zeroshot_ner_deid_subentity_docwise_medium`.

*NER* stands for **Named Entity Recognition** — the model has been trained to read
a sentence and label the important pieces:

> *"Patient **Daniel Foster** was seen by **Dr. Henry Seven** on **August 6, 2012**."*

The model reads this and returns:
- `Daniel Foster` → label: **PATIENT**
- `Dr. Henry Seven` → label: **DOCTOR**
- `August 6, 2012` → label: **DATE**

It can recognise 18 different types of information including names, dates, cities,
phone numbers, email addresses, usernames, and medical record numbers.

### The Rule-Based Scanners

The AI model is very good at reading context, but certain things are more reliably
caught by fixed patterns — the same way a spell-checker uses a dictionary rather
than guessing.

Four pattern-based scanners run alongside the AI model:

| Scanner | What it finds |
|---|---|
| `zip_parser` | ZIP codes and postcodes (e.g. `97006`, `M13 9PL`) |
| `date_of_birth_parser` | Dates preceded by DOB labels |
| `email_matcher` | Email addresses |
| `country_matcher` | Country names |

The results from all five sources are merged together. If two detectors flag the
same piece of text, the longer / more specific match wins.

---

## Checkpoint 2 — Applying the Rules

Once the pipeline has a list of detected items and their labels, a custom piece of
code (called a **UDF** — User-Defined Function) goes through each one and decides
what to do:

```
Label = PATIENT      →  look up Patient ID in the database
Label = DOCTOR       →  do nothing, leave it as-is
Label = DATE         →  keep only the month and year
Label = DOB          →  calculate the person's age
Label = ZIP          →  keep first 3 characters, replace the rest with X
Label = SSN          →  replace with [SSN]
Label = PHONE        →  replace with [PHONE]
Label = EMAIL        →  replace with [EMAIL]
… and so on
```

Replacements are made from the **end of the document backwards**. This is a
technical trick — if you replace text from the beginning, the positions of
everything after it shift, and the next replacement lands in the wrong place.
Working backwards avoids that problem.

---

## How XML / CDA Files Are Handled Differently

Plain text and XML medical records need slightly different treatment.

XML files (like HL7 CDA documents used in hospitals) are structured — information
sits in specific, labelled locations:

```xml
<birthTime value="19470501"/>          ← date of birth is always here
<postalCode>97006</postalCode>         ← ZIP is always here
<given>Myra</given><family>Jones</family>  ← patient name is always here
```

For these known locations, the pipeline goes **directly to the right tag and
changes the value** — no AI needed, because the structure tells us exactly what
each piece of data is.

For the **narrative sections** (free-flowing clinical notes written by doctors),
the same rules as plain text apply: find dates, names, and codes using patterns,
then replace them.

---

## Why We Kept Doctors' Names

A deliberate design decision: **doctor names are never removed**.

The AI model reliably tells the difference between a `DOCTOR` label and a `PATIENT`
label, so in the replacement step the code simply skips any item labelled `DOCTOR`.

This matters because care teams reviewing de-identified records still need to know
which clinician authored a note or performed a procedure.

---

## What Gets Saved at the End

After the pipeline finishes, two files are created:

| File | What it contains |
|---|---|
| `file9_deid.xml` (or de-identified text) | The original document with all PHI replaced |
| `XML_DeID_Results.xlsx` | A log of every single change made — what was found, where it was, what it was replaced with |

The Excel log is colour-coded:
- **Orange column** — the original sensitive value
- **Green column** — what it was replaced with

This makes it easy to review and audit the de-identification without having to
compare the two documents manually.

---

## Summary

```
Document in
    │
    ├─ Structured XML fields → direct tag rules (fast, exact)
    │
    └─ Free text sections ──→ AI model + pattern scanners
                                        │
                                        ▼
                              Custom replacement rules
                              (patient ID / age / month+year / partial ZIP)
                                        │
                                        ▼
                              De-identified document + Excel audit log
```

The whole process runs automatically — no manual review needed for standard cases.
The Excel log lets a human spot-check the results at any time.
