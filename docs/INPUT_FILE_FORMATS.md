# Understanding the Input File Formats

*A detailed plain-language guide — no coding or technical background needed.*

---

## Part 1 — What Kind of Files Are These?

### They are XML files disguised as .txt files

All 10 files in the `analysis/` folder are saved with a `.txt` extension, but they are
actually **XML files** — a specific type of structured text that computers use to store
and share information in an organised way.

If you opened one in a text editor you would see lines like this (real example from `file5.txt`):

```xml
<given>Myra</given>
<family>Jones</family>
<birthTime value="19470501"/>
<postalCode>97006</postalCode>
<telecom value="tel:(816)276-6909"/>
```

Each piece of information is wrapped in angle brackets `< >` called **tags**.
The tag is the label. The text between the opening and closing tags is the value.

---

## Part 2 — What Is XML? (The Filing Cabinet Analogy)

Imagine a large metal filing cabinet in a hospital records room.

- The **cabinet** itself is the XML file.
- Each **drawer** has a label on it — for example *"Patient Name"*, *"Date of Birth"*,
  *"ZIP Code"*, *"Allergies"*.
- The **contents of each drawer** are the actual values — *"Myra Jones"*, *"01/05/1947"*,
  *"97006"*, *"Penicillin G benzathine — Hives — Moderate"*.

The power of XML is that **every hospital using this format puts the same information in
the same drawer**. A different hospital that receives this file knows exactly where to
look for the patient's ZIP code — it is always in the `<postalCode>` drawer. No guessing.

This is why the de-identification pipeline can work automatically — it knows exactly
which drawers contain sensitive personal information.

---

## Part 3 — The Standards Behind the Format

### HL7 — the rules organisation

**HL7** stands for *Health Level 7*. It is the international not-for-profit organisation
that writes the rules for how electronic medical records must be structured. Think of it
as the international standards body — like the organisation that decides what traffic
lights must look like so that every country uses red for stop and green for go.

Every file in this project follows HL7 rules.

### CDA — the document format

**CDA** stands for *Clinical Document Architecture*. It is the specific HL7 rulebook that
defines how a clinical document (a medical record) must be laid out. All 10 files are CDA
documents.

You can tell a file is CDA because the very first content line always looks like this
(real example from `file1.txt`):

```xml
<ClinicalDocument xmlns="urn:hl7-org:v3" ...>
```

- `ClinicalDocument` — the name of the document type
- `xmlns="urn:hl7-org:v3"` — this is the "stamp" that says it follows the HL7 version 3
  standard. Every single file in this project has this stamp.

### CCD — a specific type of CDA document

**CCD** stands for *Continuity of Care Document*. It is a specific flavour of CDA
designed to carry a **complete health summary** of a patient — so that if a patient moves
from one hospital to another, all their important health history travels with them.

A CCD contains all of these sections in one document:
- Patient demographics (name, address, DOB, phone, SSN)
- Active problems and diagnoses
- Current medications
- Allergies and reactions
- Vital signs (weight, blood pressure, etc.)
- Immunisation history
- Lab results
- Upcoming care plans

You can tell a file is a CCD document by looking for this line near the top:

```xml
<templateId root="2.16.840.1.113883.10.20.22.1.2"/>
```

That long number (`2.16.840.1.113883.10.20.22.1.2`) is the official **identity code** of
the CCD format — like a barcode that says "this is a Continuity of Care Document".

Also, CCD files always have this code:

```xml
<code code="34133-9" displayName="Summarization of episode note"/>
```

`34133-9` is the LOINC code (medical coding system) for a patient health summary.

---

## Part 4 — The Three Groups in This Project

After inspecting all 10 files, they fall into three clearly different groups.

---

### Group A — Files 1, 2, 3, 4 — Standard CCD (Full Health Summary)

These are **modern, automatically generated** CCD documents.
They were created by a system called **Synthea** — a tool that generates realistic but
completely fictional patient data for testing healthcare software. You can see this in the
file:

```xml
<softwareName>https://github.com/synthetichealth/synthea</softwareName>
```

#### What they contain

Each file is a different patient with a complete health history:
- `file1.txt` — Bryce Zemlak, born 03 December 1967, Worcester, Massachusetts
- `file2.txt` — Elizabeth Itasca
- `file3.txt` — Kimberly Olympic
- `file4.txt` — Grant Custer

Real example from the top of `file1.txt`:

```xml
<title>Continuity of Care Document</title>
<effectiveTime value="20200823022916"/>
...
<streetAddressLine>286 Leuschke Branch</streetAddressLine>
<city>Worcester</city>
<state>Massachusetts</state>
<postalCode>01606</postalCode>
...
<given>Bryce</given>
<family>Zemlak</family>
...
<birthTime value="19671203012916"/>
```

#### How the structure looks

```
file1.txt (Bryce Zemlak)
│
├── Header
│   ├── Patient name, address, ZIP, phone, DOB, SSN
│   └── Treating doctor, hospital name
│
└── Sections (medical content)
    ├── Allergies
    ├── Medications
    ├── Problems / Diagnoses
    ├── Vital Signs
    ├── Immunisations
    ├── Procedures
    ├── Lab Results
    └── Care Plan
```

#### PHI (sensitive information) found in these files

| Where in the file | What sensitive data | Example |
|---|---|---|
| `<given>` + `<family>` tags | Patient name | Bryce Zemlak |
| `<birthTime value="..."/>` | Date of birth (YYYYMMDD format) | 19671203 |
| `<streetAddressLine>` | Street address | 286 Leuschke Branch |
| `<city>`, `<state>` | City and state | Worcester, Massachusetts |
| `<postalCode>` | ZIP code | 01606 |
| `<telecom value="tel:..."/>` | Phone number | (816) 276-6909 |
| `<id root="2.16.840.1.113883.4.1">` | SSN (the root OID identifies it as SSN) | 000-10-5230 |
| `<effectiveTime>` | Service dates | 20200823 |

---

### Group B — Files 5, 6, 7, 8, 9 — CDA/CCD Documents (Same Patient, Repeated Visits)

These five files are **older, manually crafted CDA/CCD documents** used as reference
examples by the US standards body NIST (National Institute of Standards and Technology).
You can see this in the file comment at the top:

```xml
<!-- Title: US_Realm_Header_Template
     Revision History: 01/31/2011 ... NIST (multiple) -->
```

**All five files belong to the same patient: Myra Jones.**

Real example from `file5.txt`:

```xml
<title>Community Health and Hospitals: Health Summary</title>
...
<given>Myra</given>
<family>Jones</family>
<birthTime value="19470501"/>
<postalCode>97006</postalCode>
<telecom value="tel:(816)276-6909" use="HP"/>
<id extension="000-10-5230" root="2.16.840.1.113883.4.1"/>
```

#### Why are there five files for the same patient?

These files represent the **same reference document duplicated** — they are copies of the
same NIST example CDA file, used to test how the pipeline handles repeated patient records
in a batch. In a real hospital scenario, this would represent the same patient's record
distributed across multiple systems or locations.

#### How Group B differs from Group A

| | Group A (files 1–4) | Group B (files 5–9) |
|---|---|---|
| Created by | Synthea (automated) | NIST (manually authored) |
| Age of format | 2020 (modern) | 2011–2014 (older) |
| Structure | Clean, minimal attributes | More detailed, with comments throughout |
| Number of namespaces | 2 | 7 (more verbose) |
| Sections | Modern standard sections | Classic CCD sections |
| Patient | Different patient per file | Same patient (Myra Jones) in all 5 |

Despite these differences, both groups use the **same PHI drawer labels** — `<given>`,
`<family>`, `<birthTime>`, `<postalCode>`, etc. The de-identification pipeline reads the
same drawers in both.

#### The doctor in these files

An interesting detail in files 5–9: the treating doctor is **Dr. Henry Seven** —
the same name used in the custom pipeline test cases. Dr. Henry Seven appears multiple
times in each file (as the treating physician, data enterer, and authenticator):

```xml
<assignedPerson>
  <name>
    <prefix>Dr</prefix>
    <given>Henry</given>
    <family>Seven</family>
  </name>
</assignedPerson>
```

The pipeline correctly keeps doctor names as-is and does not replace them.

---

### Group C — File 10 — "Refill Summary" (A Different Document Type)

`file10.txt` belongs to a different patient (**Minh Kulas**) and is a fundamentally
different kind of document — not a full health summary, but a **subsequent evaluation note**,
which is what a hospital generates for a follow-up visit or prescription refill.

Real example from the top of `file10.txt`:

```xml
<code code="11506-3" displayName="Subsequent evaluation note"/>
<title>Refill Summary</title>
```

`11506-3` is the LOINC code for a follow-up/evaluation note — completely different from
`34133-9` (full health summary) used by Groups A and B.

#### What a "Refill Summary" contains vs a full CCD

| Section | Full CCD (Groups A & B) | Refill Summary (file10) |
|---|---|---|
| Patient demographics | Full — name, DOB, address, phone, SSN | Present but briefer |
| Allergies | Full list | May be abbreviated |
| Medications | Full history | Focused on current prescriptions |
| Problems / Diagnoses | Complete problem list | Current visit reason only |
| Vital signs | Detailed | May be limited |
| Immunisations | Full history | Usually absent |
| Lab results | Full history | Usually absent |

Think of it this way:
- **Full CCD** = A complete medical passport — everything about the patient's history
- **Refill Summary** = A short visit note — what happened at one specific appointment

#### PHI in file10

Even though it is a shorter document, it still contains the same types of PHI in the
same tag locations:

```xml
<given>Minh</given>
<family>Kulas</family>
<birthTime value="..."/>
<postalCode>...</postalCode>
```

The pipeline finds and de-identifies these correctly, which is why file10 still produced
41 changes in the batch run.

---

## Part 5 — The Key Difference: Where the Dates Are Stored

One important thing to understand is that **dates in CDA XML are not written as humans
read them**. They are stored as numbers in YYYYMMDD format:

| What it means | How it looks in the file | How it looks to a human |
|---|---|---|
| Date of birth: 1 May 1947 | `<birthTime value="19470501"/>` | 01/05/1947 |
| Service date: 6 August 2012 | `<effectiveTime value="20120806"/>` | August 6, 2012 |
| Date created: 23 August 2020 | `<effectiveTime value="20200823022916"/>` | 23 Aug 2020 |

The pipeline handles this automatically. Pass 1 converts `19470501` into an age
(*78 years old*) and `20120806` into a month/year (*August 2012*).

---

## Part 6 — How the Pipeline Handles All Three Groups

### Pass 1 — Going straight to the labelled drawers

Pass 1 reads the XML structure and goes directly to the drawers where PHI is always
stored — regardless of which group the file belongs to.

```
All three groups share these drawer labels:
                                                
  <birthTime value="YYYYMMDD"/>   → Date of birth → converted to age
  <postalCode>XXXXX</postalCode>  → ZIP code      → partially masked (970XX)
  <given> + <family>              → Patient name  → replaced with PT-XXXXX
  <telecom value="tel:..."/>      → Phone number  → replaced with [PHONE]
  <streetAddressLine>             → Address       → replaced with [STREET]
  <id root="SSN OID">             → SSN           → replaced with [SSN]
  <effectiveTime>                 → Service date  → shortened to Month YYYY
```

These labels are the same in Group A, Group B, and Group C — because all three follow
the same HL7 CDA rules.

### Pass 2 — AI reading all text

Pass 2 runs the ZeroShot NER (artificial intelligence) model on every piece of text in
the document — table cells, narrative notes, section headers, everything. It does not
care about XML tags at all. Whether the file is a full CCD or a short refill note, the
AI reads every sentence and finds PHI the same way.

This is why the pipeline works on any CDA/CCD file without needing to know the document
type in advance.

---

## Part 7 — What Would Happen with a Different File Format

The 10 files in this project are all HL7 CDA/CCD documents.
Here is what would happen if a different type of file were added:

| New file type | Pass 1 (structural rules) | Pass 2 (AI) | Action needed |
|---|---|---|---|
| Another CDA or CCD file | Works perfectly | Works perfectly | None |
| FHIR XML (newer standard) | Some drawer labels differ | Still works | Update Pass 1 tag rules |
| Custom hospital XML schema | Drawer labels are different | Still works | Update Pass 1 tag rules |
| Plain text clinical note | Not applicable | Works perfectly | None |
| PDF | Cannot be read | Not applicable | Add PDF text extraction step |

**The key point:** Pass 2 (the AI model) is always format-agnostic. Only Pass 1 needs
updating when a new XML format is introduced — and only the structural rules section
needs to change, not the AI model.

---

## Part 8 — Summary of All 10 Files

| File | Patient | Document Type | Created By | Year |
|---|---|---|---|---|
| file1.txt | Bryce Zemlak | Full CCD — Health Summary | Synthea (generated) | 2020 |
| file2.txt | Elizabeth Itasca | Full CCD — Health Summary | Synthea (generated) | 2020 |
| file3.txt | Kimberly Olympic | Full CCD — Health Summary | Synthea (generated) | 2020 |
| file4.txt | Grant Custer | Full CCD — Health Summary | Synthea (generated) | 2020 |
| file5.txt | Myra Jones | CCD — Health Summary | NIST (manual reference) | 2014 |
| file6.txt | Myra Jones | CCD — Health Summary | NIST (manual reference) | 2014 |
| file7.txt | Myra Jones | CCD — Health Summary | NIST (manual reference) | 2014 |
| file8.txt | Myra Jones | CCD — Health Summary | NIST (manual reference) | 2014 |
| file9.txt | Myra Jones | CCD — Health Summary | NIST (manual reference) | 2014 |
| file10.txt | Minh Kulas | CDA — Refill/Evaluation Note | Synthea (generated) | 2020 |

### De-identification results at a glance

| File | Pass 1 changes | Pass 2 (AI) changes | Total |
|---|---|---|---|
| file1.txt | ~25 | ~10 | 35 |
| file2.txt | ~12 | ~9 | 21 |
| file3.txt | ~12 | ~8 | 20 |
| file4.txt | ~12 | ~8 | 20 |
| file5–9.txt | 132 each | 55 each | 187 each |
| file10.txt | ~31 | ~10 | 41 |

Files 5–9 have many more changes because Myra Jones's record is a densely authored
reference document with extensive narrative text, repeated personal details throughout,
and multiple participants (doctor, spouse, grandparent) all carrying PHI.

---

## Quick Reference — Glossary

| Term | Plain-language meaning |
|---|---|
| **XML** | A way of organising information using labelled tags (like a filing cabinet with labelled drawers) |
| **HL7** | The international organisation that writes the rules for medical record formats |
| **CDA** | The HL7 document format used by all 10 files in this project |
| **CCD** | A specific type of CDA document — a complete patient health summary |
| **templateId** | A barcode-like number that identifies which type of document it is |
| **LOINC code** | A standardised code number that labels the type of medical document or observation |
| **YYYYMMDD** | The date format used inside CDA files — year first, then month, then day |
| **NIST** | US National Institute of Standards and Technology — produced the reference example files (files 5–9) |
| **Synthea** | A software tool that generates realistic but entirely fictional patient data (files 1–4, file10) |
| **Pass 1** | The pipeline step that uses XML tag knowledge to find PHI in known locations |
| **Pass 2** | The pipeline step that uses AI to find PHI in any text, regardless of XML structure |
| **PHI** | Protected Health Information — any data that could identify a patient |
