# Understanding the Input XML Files

*Plain-language guide — no technical background needed.*

---

## What Are These Files?

The 10 files in the `analysis/` folder are **electronic medical records**.
Even though they are saved with a `.txt` extension, they are actually XML files —
structured documents that hospitals and clinics use to store and share patient
information digitally.

Think of XML as a filing cabinet where every drawer has a label, and every folder
inside has a label too. The labels tell you exactly what type of information is stored
inside. For example:

```
<birthTime value="19470501"/>        ← this drawer holds: date of birth
<postalCode>97006</postalCode>       ← this drawer holds: ZIP code
<given>Myra</given>                  ← this drawer holds: first name
```

The labels are consistent — every hospital using this format puts the date of birth
in the same drawer. That is what makes structured records powerful.

---

## The Two Standards You Need to Know

### HL7 CDA — the container

**HL7** stands for *Health Level 7* — it is the international organisation that sets
the rules for how health information is structured and shared between hospitals,
clinics, and software systems.

**CDA** stands for *Clinical Document Architecture* — the specific rulebook that says
how an electronic medical record must be laid out. All 10 files in this project follow
the CDA rulebook.

### CCD — a specialised type of CDA

**CCD** stands for *Continuity of Care Document*. It is a specific kind of CDA document
designed to give a *complete health summary* of a patient — covering allergies,
medications, problems, vital signs, immunisations, and so on. Think of it as the
standard form a doctor fills in when transferring a patient to another hospital.

---

## The Three Types of Files in This Project

After inspecting all 10 files, they fall into three groups:

### Group A — Files 1 to 4 — Standard CCD (Health Summary)

These are full patient health summaries. They contain a complete picture:
- Patient demographics (name, DOB, address, contact details)
- Active problems and diagnoses
- Current medications
- Allergies
- Vital signs
- Immunisation history
- Upcoming care plans

**What this means for de-identification:** These files contain the most PHI
(personal health information) — names, dates, addresses, phone numbers, SSNs
are all present and spread throughout the document.

---

### Group B — Files 5 to 9 — CDA with CCD structure (same patient)

These five files all belong to **the same patient: Myra Jones**.
They use the same CCD layout as Group A, but they represent
repeated encounters — follow-up visits, check-ins, or continuing care notes.

The structure is identical to Group A, which is why the pipeline processes them
the same way. The slightly higher change counts in the batch results (187 per file)
are because Myra Jones has more visits documented.

---

### Group C — File 10 — "Refill Summary" (a different document type)

File 10 belongs to **Minh Kulas** and is a different type of document —
a *subsequent evaluation note* or *refill summary*. Instead of a full health
summary, it captures a specific encounter (e.g., a prescription refill visit).

| | Group A/B (CCD health summary) | Group C (refill note) |
|---|---|---|
| Covers | Complete patient history | One specific visit/encounter |
| Length | Longer — many sections | Shorter — focused |
| PHI present | Extensive | Less — mainly name, date, prescriptions |

The pipeline handles this file correctly — it just finds a different profile of PHI.

---

## How the Three Groups Look Different (Without Technical Jargon)

Imagine three types of forms a doctor might fill in:

| Form type | Equivalent in these files |
|---|---|
| New patient intake form (full history) | Files 1–4 — standard CCD |
| Follow-up visit notes for a known patient | Files 5–9 — repeated CDA/CCD |
| Prescription renewal slip | File 10 — refill/evaluation note |

All three forms come from the same filing system (HL7 CDA).
The overall layout is the same — same drawer labels for names, dates, ZIPs.
The difference is in how much information is filled in and which sections exist.

---

## Does the Format Affect the De-Identification Pipeline?

**No — all three groups are handled correctly by the pipeline.** Here is why:

### Pass 1 — Structural rules
Pass 1 goes directly to known drawer labels (XML tag names) like
`birthTime`, `postalCode`, `patient/name`, and `telecom`.
Because all three groups follow the same HL7 CDA rules, the drawer labels
are always in the same place. The pipeline finds them reliably in every file.

### Pass 2 — AI (ZeroShot NER)
Pass 2 reads all the text in the document, regardless of which section it
appears in or what the document type is. Whether the file is a full health summary
or a short refill note, the AI reads every sentence and flags PHI the same way.

---

## What Would Break the Pipeline

The pipeline is designed for **HL7 CDA / CCD documents**.
If a different type of file were added, here is what would happen:

| File type added | Pass 1 | Pass 2 |
|---|---|---|
| Another CDA or CCD document | Works perfectly | Works perfectly |
| FHIR XML (a newer format) | Some drawer labels differ — needs updates | Still works — reads text regardless |
| Plain text note (no XML) | Not applicable | Works perfectly |
| PDF | Cannot be parsed | Not applicable without text extraction |
| Custom hospital XML | Drawer labels are different — needs updates | Still works |

---

## Summary

```
All 10 files
     │
     ├── Files 1–4 ────── Standard CCD (full health summary)
     │                    Most PHI, most sections, new patients
     │
     ├── Files 5–9 ────── CDA with CCD layout (same patient, repeated visits)
     │                    Same structure as Group A, same patient (Myra Jones)
     │
     └── File 10 ──────── CDA — refill/evaluation note
                          Shorter, fewer sections, different patient (Minh Kulas)

All three groups:
  ✓ Same root format (HL7 CDA)
  ✓ Same drawer label names for PHI
  ✓ Handled correctly by Pass 1 and Pass 2
  ✓ No pipeline changes needed
```
