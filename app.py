from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd

import os
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

USE_CASES = {
    "CSV Upload Validation",
    "Duplicate Asset Detection",
    "Pickup Scheduling Confirmation",
    "Donor Asset Data Validation",
    "Donation Commitment vs Actual Reconciliation",
    "Data Privacy Compliance",
    "Donation Tax Certificate Issuance",
    "Asset Return or Cancellation Request",
    "Receiving Assets from Donor",
    "Partner Asset Classification",
    "Rescheduling & Location Mismatch",
    "Partner to Beneficiary Handoff",
    "Multiple Pickups in Phases",
    "Inventory Overstock Management",
    "Partner Skill/Capability Mismatch",
    "Partner Non-compliance or SLA Breach",
    "Receipt Confirmation",
    "Device Condition Feedback",
    "Feedback on Usability",
    "Multiple Deliveries Tracking",
    "Unauthorized Asset Usage",
    "Beneficiary Accessibility Issues",
    "Lost or Stolen Asset Report",
    "Donor Budget vs Execution Reconciliation",
    "Expense Tracking vs Asset Flow",
    "Audit Trail & Compliance Reporting",
    "Budget Variance Forecasting",
    "Regulatory Compliance Check",
    "Multi-project Resource Allocation",
}
USE_CASE_SOLUTIONS = {
    "CSV Upload Validation":
        "Simple binary validation. System accepts or rejects the upload. No chatbot needed.",

    "Duplicate Asset Detection":
        "AI chatbot detects duplicates, alerts donor instantly, reduces manual cleanup.",

    "Pickup Scheduling Confirmation":
        "Bot reconciles scheduled assets vs CSV upload, alerts mismatch, prompts correction.",

    "Donor Asset Data Validation":
        "Bot can query donor to fill missing data or correct errors interactively.",

    "Donation Commitment vs Actual Reconciliation":
        "Bot helps compare commitment vs upload and pickup, alerts donor or admin for mismatches.",

    "Data Privacy Compliance":
        "Bot verifies consent flags, requests missing consents interactively to ensure compliance.",

    "Donation Tax Certificate Issuance":
        "Bot auto-generates certificates, notifies donors, and tracks issuance status.",

    "Asset Return or Cancellation Request":
        "Bot manages cancellation workflows, approves or refers to admin, updates records.",

    "Receiving Assets from Donor":
        "Chatbot reconciles expected vs received assets and flags discrepancies for approval.",

    "Partner Asset Classification":
        "AI-powered image recognition bot suggests correct classification and reduces manual errors.",

    "Rescheduling & Location Mismatch":
        "Bot tracks schedules, alerts all parties, suggests new timings, and confirms.",

    "Partner to Beneficiary Handoff":
        "Bot records asset condition, confirms quantities, and alerts admin on discrepancies.",

    "Multiple Pickups in Phases":
        "Chatbot tracks phased pickups, aggregates data, and sends reminders for incomplete pickups.",

    "Inventory Overstock Management":
        "Bot detects overcapacity and suggests redistribution or pickup rescheduling.",

    "Partner Skill/Capability Mismatch":
        "Bot flags assets needing specialized handling and routes them to expert partners.",

    "Partner Non-compliance or SLA Breach":
        "Bot monitors SLA data, sends warnings, and escalates persistent issues.",

    "Receipt Confirmation":
        "Bot prompts for receipt confirmation and sends reminders until acknowledged.",

    "Device Condition Feedback":
        "Bot collects condition reports with photos and triggers alerts for replacements.",

    "Feedback on Usability":
        "Bot sends automated surveys and collects structured usability feedback.",

    "Multiple Deliveries Tracking":
        "Bot aggregates deliveries and shows clear history and status.",

    "Unauthorized Asset Usage":
        "Bot monitors usage logs, flags anomalies, and alerts admin for investigation.",

    "Beneficiary Accessibility Issues":
        "Bot collects accessibility issues via feedback and coordinates logistics resolution.",

    "Lost or Stolen Asset Report":
        "Bot logs reports, initiates claims workflows, and notifies donor and admin.",

    "Donor Budget vs Execution Reconciliation":
        "Bot reconciles donation value against promised budget and flags shortfalls or overruns.",

    "Expense Tracking vs Asset Flow":
        "Bot analyzes financial data against asset logs and alerts admins of anomalies.",

    "Audit Trail & Compliance Reporting":
        "Bot ensures all handoffs are logged and auto-generates audit-ready summaries.",

    "Budget Variance Forecasting":
        "Bot analyzes historical trends and predicts budget variances for review.",

    "Regulatory Compliance Check":
        "Bot tracks deadlines, verifies document completeness, and escalates non-compliance.",

    "Multi-project Resource Allocation":
        "Bot recommends resource redistribution based on priority and availability."
}

RECONCILIATION_CASES = {
    "Donation Commitment vs Actual Reconciliation",
    "Donor Budget vs Execution Reconciliation",
    "Expense Tracking vs Asset Flow",
}

VALIDATION_CASES = {
    "CSV Upload Validation",
    "Donor Asset Data Validation",
    "Duplicate Asset Detection",
}

PROCESS_CASES = USE_CASES - RECONCILIATION_CASES - VALIDATION_CASES
def handle_use_case_row(row):
    use_case = row["use_case"]

    if use_case not in USE_CASES:
        return {
            "use_case": use_case,
            "status": "INVALID_USE_CASE",
            "severity": "HIGH",
        }

    if use_case in RECONCILIATION_CASES:
        sent = int(row.get("sent", 0))
        received = int(row.get("received", 0))
        diff = sent - received
        status = "MATCH" if diff == 0 else "MISMATCH"
        severity = "HIGH" if diff != 0 else "NONE"

    elif use_case in VALIDATION_CASES:
        sent = received = diff = 0
        status = "VALIDATION_REQUIRED"
        severity = "MEDIUM"

    else:
        sent = received = diff = 0
        status = "PROCESS_EVENT"
        severity = "MEDIUM"

    return {
        "use_case": use_case,
        "source": row.get("source", ""),
        "target": row.get("target", ""),
        "sent": sent,
        "received": received,
        "difference": diff,
        "status": status,
        "severity": severity,
        "metadata": row.get("metadata", ""),
    }
def generate_llm_solution(result):
    prompt = f"""
Use case: {result['use_case']}
Source: {result['source']}
Target: {result['target']}
Status: {result['status']}

Explain the resolution clearly for an admin.
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        return response.text

    except Exception as e:
        return f"LLM unavailable due to quota or rate limits. Suggested action: {USE_CASE_SOLUTIONS.get(result['use_case'], 'Manual review required.')}"




@app.post("/run-use-cases")
async def run_use_cases(file: UploadFile = File(...)):
    try:
        df = pd.read_csv(file.file)
    except Exception:
        raise HTTPException(400, "Invalid CSV format")

    if "use_case" not in df.columns:
        raise HTTPException(400, "use_case column missing")

    results = []

    for _, row in df.iterrows():
        result = handle_use_case_row(row)

        if result["status"] == "INVALID_USE_CASE":
            result["solution"] = "Rejected: use_case not recognized."
        elif result["use_case"] == "CSV Upload Validation":
            result["solution"] = USE_CASE_SOLUTIONS["CSV Upload Validation"]
        else:
            result["solution"] = generate_llm_solution(result)

        results.append(result)

    return {
        "total": len(results),
        "results": results
    }
