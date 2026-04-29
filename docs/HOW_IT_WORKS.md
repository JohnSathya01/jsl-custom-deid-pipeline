# How the De-Identification Pipeline Works

*Plain-language guide — no coding experience needed.*

---

## What Problem Does It Solve?

Medical records contain sensitive personal information — patient names, dates of birth, social security numbers, addresses, phone numbers, and more.

Before sharing these records for research, audits, or transfers, that information must be **removed or replaced** so no one can identify the patient. This process is called **de-identification**.

The pipeline does this automatically, following five specific rules:

| What was found | What happens to it |
|---|---|
| **Patient name** (e.g. *Myra Jones*) | Replaced with a Patient ID (e.g. *PT-00001*) |
| **Doctor name** (e.g. *Dr. Henry Seven*) | Left exactly as-is — not changed |
| **Service date** (e.g. *08/06/2012*) | Shortened to month and year only (e.g. *August 2012*) |
| **Date of birth** (e.g. *01/05/1947*) | Converted to the patient's current age (e.g. *78 years old*) |
| **ZIP / postcode** (e.g. *97006*) | First 3 digits kept, rest replaced with X (e.g. *970XX*) |

Everything else — SSN, phone number, email, street address — is replaced with a placeholder like `[SSN]`, `[PHONE]`, or `[STREET]`.

---

## Two Types of Documents, Two Approaches

The pipeline handles two very different types of medical records:

| Document type | Example | How it is processed |
|---|---|---|
| **Plain text** | Clinical notes, discharge summaries, typed reports | Approach 1 — AI reads the text and labels PHI |
| **XML files** (HL7 CDA, FHIR, etc.) | Electronic health records, hospital data exports | Approach 2 — Structural rules + AI on text sections |

---

## Approach 1 — Plain Text Pipeline

Used by: `Custom_DeID_Pipeline.ipynb` and `Test_Cases_DeID.ipynb`

Think of this as an assembly line with two stations:

```
Plain text in
      │
      ▼
┌─────────────────────────────────────┐
│  STATION 1 — "Find the PHI"         │
│                                     │
│  • AI model reads each sentence     │
│    and labels names, dates, ZIPs…   │
│                                     │
│  • Pattern scanners check for       │
│    ZIPs, DOBs, emails, countries    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STATION 2 — "Replace it"           │
│                                     │
│  Each detected item goes through    │
│  the five rules                     │
└──────────────┬──────────────────────┘
               │
               ▼
      De-identified text
```

### Station 1 — Finding the PHI

**The AI model** reads every sentence and labels the sensitive pieces:

> *"Patient **Myra Jones** was seen by **Dr. Henry Seven** on **August 6, 2012**."*

The model returns:
- `Myra Jones` → **PATIENT**
- `Dr. Henry Seven` → **DOCTOR**
- `August 6, 2012` → **DATE**

It recognises 18 types of information: names, dates, cities, phone numbers, emails, SSNs, medical record numbers, usernames, and more.

**The pattern scanners** run alongside the AI and catch things that always follow a fixed format — ZIPs, email addresses, and dates of birth. Think of them like a spell-checker using a dictionary rather than guessing. They never miss a pattern they were built to recognise.

Both results are combined. If the AI and a scanner both flag the same word, the more specific match wins.

### Station 2 — Replacing the PHI

Once every sensitive item is labelled, the replacement rules run:

```
PATIENT  →  look up Patient ID
DOCTOR   →  do nothing, keep as-is
DATE     →  keep month and year only
DOB      →  calculate the person's age today
ZIP      →  keep first 3 characters + XXs
SSN      →  [SSN]
PHONE    →  [PHONE]
EMAIL    →  [EMAIL]
…and so on
```

---

## Approach 2 — XML Pipeline

Used by: `XML_DeID_Pipeline.ipynb`

XML medical records (like HL7 CDA documents used in hospitals) have a specific structure. Information sits in labelled slots:

```xml
<birthTime value="19470501"/>           ← DOB always lives here
<postalCode>97006</postalCode>          ← ZIP always lives here
<given>Myra</given><family>Jones</family>  ← name always lives here
```

Because we know exactly where PHI sits in a structured document, we can go directly to the right place and change it — no AI guessing needed for those fields.

But XML records also contain **free-text narrative sections** — doctors' notes written in plain English, sitting inside `<text>` blocks. Those sections need the same AI treatment as Approach 1.

So the XML pipeline runs two passes:

```
XML document in
      │
      ├── PASS 1 ── Structural rules ──────────────────────────────────────────┐
      │             Goes directly to known tag locations:                       │
      │             birthTime → age                                             │
      │             postalCode → 970XX                                          │
      │             patient name tags → PT-00001                                │
      │             SSN id tag → [SSN]                                          │
      │             telecom phone → [PHONE]                                     │
      │             effectiveTime service dates → August 2012                   │
      │             streetAddressLine → [STREET]                                │
      │                                                                         │
      └── PASS 2 ── AI (ZeroShot NER) — primary detection ───────────────────┘
                    Before sending any text to the AI, a plain-English label
                    is added: "Date of birth: 19470501", "ZIP code: 97006".
                    This gives the model enough context to understand what it
                    is reading, even for values that look like raw codes.
                    Full narrative sections are extracted as complete blocks
                    rather than small fragments, so the AI reads sentences in
                    context — just like a human reviewer would.

                                        │
                                        ▼
                             De-identified XML + Excel audit log
```

### Why two passes?

| | Pass 1 | Pass 2 |
|---|---|---|
| What it handles | Structured fields at known tag/attribute locations | All text in the document — narrative, table cells, comments |
| How it works | Reads the XML tag directly | JSL ZeroShot NER with context-enriched inputs |
| Speed | Very fast | Slower (AI model) |
| Why it is enough for structured fields | The tag name tells us exactly what the data is — no ambiguity | — |
| Why AI is the primary mechanism | Pass 1 covers predictable structure; Pass 2 is the safety net that catches everything else regardless of where it appears | — |
| Context enrichment | — | Raw values like `19470501` are labelled before sending to the AI: `"Date of birth: 19470501"` — this dramatically improves accuracy |

### Works on any XML structure

Pass 2 does not know or care about tag names. It walks every single text node in the document and runs the AI on it. This means the pipeline works on **CDA, FHIR, custom XML formats**, or any other XML structure without any changes.

---

## Why Doctor Names Are Never Removed

A deliberate design decision: **doctor names are always kept**.

The AI model reliably distinguishes a `DOCTOR` label from a `PATIENT` label. In the replacement step, the code simply skips anything labelled `DOCTOR`.

Care teams reviewing de-identified records still need to know which clinician authored a note or performed a procedure.

---

## What Gets Saved at the End

After the pipeline finishes, two files are created:

| File | What it contains |
|---|---|
| De-identified document | The original record with all PHI replaced |
| Excel audit log (`.xlsx`) | Every single change — what was found, where, what it became |

The Excel log is colour-coded:
- **Orange column** — the original sensitive value
- **Green column** — what it was replaced with

This makes auditing straightforward — no need to compare two documents manually.

---

## Summary

```
Plain text                         XML document
     │                                  │
     ▼                                  ├── Pass 1: direct tag rules
AI model + pattern scanners             │   (fast, exact, any XML schema)
     │                                  │
     ▼                                  └── Pass 2: AI on all text nodes
Five replacement rules                              │
     │                                              ▼
     └──────────────────────────────► De-identified output + Excel audit log
```
