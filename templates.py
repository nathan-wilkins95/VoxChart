"""
templates.py
Built-in and custom note templates for VoxChart.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

CUSTOM_TEMPLATES_FILE = Path("custom_templates.json")
logger = logging.getLogger("voxchart.templates")

BUILT_IN: dict[str, str] = {
    "SOAP Note": (
        "S (Subjective):\n"
        "  Chief Complaint: [chief complaint]\n"
        "  HPI: [history of present illness]\n"
        "  Medications: [current medications]\n"
        "  Allergies: [allergies]\n\n"
        "O (Objective):\n"
        "  Vitals: BP [  /  ]  HR [  ]  RR [  ]  Temp [  ]  SpO2 [  ]%\n"
        "  Physical Exam: [findings]\n"
        "  Labs/Imaging: [results]\n\n"
        "A (Assessment):\n"
        "  Diagnosis: [primary diagnosis]\n"
        "  Differential: [differential diagnoses]\n\n"
        "P (Plan):\n"
        "  Treatment: [treatment plan]\n"
        "  Medications: [new or changed medications]\n"
        "  Follow-Up: [follow-up instructions]\n"
        "  Patient Education: [education provided]\n"
    ),
    "HPI": (
        "History of Present Illness:\n"
        "  Onset: [when did it start]\n"
        "  Location: [where]\n"
        "  Duration: [how long]\n"
        "  Character: [description of symptom]\n"
        "  Aggravating Factors: [what makes it worse]\n"
        "  Relieving Factors: [what makes it better]\n"
        "  Timing: [constant / intermittent / frequency]\n"
        "  Severity: [0-10 pain scale]\n"
        "  Associated Symptoms: [related symptoms]\n"
    ),
    "Discharge Summary": (
        "DISCHARGE SUMMARY\n"
        "Date: [date]\n"
        "Patient: [name]  DOB: [dob]  MRN: [mrn]\n\n"
        "Admitting Diagnosis: [diagnosis]\n"
        "Discharge Diagnosis: [diagnosis]\n"
        "Attending Physician: [name]\n\n"
        "Hospital Course:\n"
        "  [summary of hospital stay]\n\n"
        "Procedures Performed:\n"
        "  [procedures]\n\n"
        "Discharge Condition: [stable / improved / critical]\n\n"
        "Discharge Medications:\n"
        "  [medication list with doses]\n\n"
        "Follow-Up Instructions:\n"
        "  [instructions]\n\n"
        "Return Precautions:\n"
        "  Return to ED if: [conditions]\n"
    ),
    "Procedure Note": (
        "PROCEDURE NOTE\n"
        "Date/Time: [date/time]\n"
        "Procedure: [procedure name]\n"
        "Indication: [indication]\n"
        "Operator: [name]  Assistant: [name]\n\n"
        "Consent: Informed consent obtained. Risks, benefits, and alternatives discussed.\n\n"
        "Technique:\n"
        "  Anesthesia: [local / general / none]\n"
        "  Position: [patient position]\n"
        "  Prep: [sterile prep description]\n"
        "  Description: [step-by-step description]\n\n"
        "Findings: [intraoperative findings]\n\n"
        "Complications: [none / describe]\n\n"
        "Specimen: [sent to pathology / none]\n\n"
        "Condition: Patient tolerated procedure well. Transferred to [location] in [condition] condition.\n"
    ),
    "Follow-Up Visit": (
        "FOLLOW-UP VISIT\n"
        "Date: [date]  Provider: [name]\n\n"
        "Reason for Visit: [reason]\n\n"
        "Interval History:\n"
        "  Since last visit: [changes / new symptoms / progress]\n"
        "  Medication Compliance: [compliant / non-compliant / issues]\n"
        "  Side Effects: [none / describe]\n\n"
        "Examination:\n"
        "  Vitals: BP [  /  ]  HR [  ]  Weight [  ]\n"
        "  Findings: [exam findings]\n\n"
        "Assessment: [updated assessment]\n\n"
        "Plan:\n"
        "  [updated plan]\n"
        "  Labs ordered: [labs]\n"
        "  Next appointment: [date/time]\n"
    ),
    "Emergency Note": (
        "EMERGENCY DEPARTMENT NOTE\n"
        "Arrival: [time]  Triage Level: [1-5]\n"
        "Chief Complaint: [complaint]\n\n"
        "HPI: [history]\n\n"
        "PMH: [past medical history]\n"
        "Meds: [medications]  Allergies: [allergies]\n\n"
        "Exam:\n"
        "  General: [appearance]\n"
        "  Vitals: BP [  /  ]  HR [  ]  RR [  ]  Temp [  ]  SpO2 [  ]%\n"
        "  [system-based findings]\n\n"
        "Workup: [labs, imaging, ECG]\n\n"
        "MDM: [medical decision making]\n\n"
        "Diagnosis: [diagnosis]\n\n"
        "Disposition: [discharge / admit / transfer]\n"
        "Condition at Disposition: [stable / critical]\n"
    ),
}


def load_custom() -> dict[str, str]:
    if not CUSTOM_TEMPLATES_FILE.exists():
        return {}
    try:
        return json.loads(CUSTOM_TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not load custom templates: %s", e)
        return {}


def save_custom(custom: dict[str, str]):
    CUSTOM_TEMPLATES_FILE.write_text(json.dumps(custom, indent=2), encoding="utf-8")


def all_templates() -> dict[str, str]:
    """Return built-in + custom templates merged."""
    merged = dict(BUILT_IN)
    merged.update(load_custom())
    return merged


def get_template(name: str) -> str | None:
    return all_templates().get(name)


def add_custom_template(name: str, body: str):
    custom = load_custom()
    custom[name] = body
    save_custom(custom)
    logger.info("Custom template saved: %s", name)


def delete_custom_template(name: str):
    custom = load_custom()
    if name in custom:
        del custom[name]
        save_custom(custom)
        logger.info("Custom template deleted: %s", name)
