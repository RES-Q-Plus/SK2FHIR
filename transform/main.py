import asyncio
import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict

import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ============ Config por variables de entorno ============
WORKDIR = Path(os.getenv("WORKDIR", "/app/workdir")).resolve()
WORKDIR.mkdir(parents=True, exist_ok=True)

# API VALIDATOR (validator-api)
VALIDATOR_BASE_URL = os.getenv("VALIDATOR_BASE_URL", "http://localhost:8085")
VALIDATOR_PATH = os.getenv("VALIDATOR_PATH", "/api/validate/bundle")
HAPI_BASE_URL = os.getenv("HAPI_BASE_URL", "").strip()  
HAPI_BEARER = os.getenv("HAPI_BEARER", "").strip()      
JOB_TAG_SYSTEM = os.getenv("JOB_TAG_SYSTEM", "https://sk_fhir/job").strip()


#Comand for the converter (MANDATORY)
#Use {in} and {out} as placeholders.
#Examples:
#   spark-submit --master local[*] C:\path\my_transform.py --input {in} --outdir {out}
#   python C:\path\my_transform.py --input {in} --outdir {out}

CONVERTER_CMD = os.getenv("CONVERTER_CMD", "").strip()

# =========================================================

app = FastAPI(title="FHIR Orchestrator API", version="1.0.0",
              description="Upload your CSV -> run your converter -> validate Bundles with validator-api")

# CORS (ajusta orígenes en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
def _tag_resource(res: dict, job_id: str):
    meta = res.setdefault("meta", {})
    tags = meta.setdefault("tag", [])
    tags.append({"system": JOB_TAG_SYSTEM, "code": job_id})

def _tag_bundle(bundle: dict, job_id: str):
    for e in bundle.get("entry") or []:
        r = e.get("resource")
        if isinstance(r, dict):
            _tag_resource(r, job_id)

async def _post_transaction(bundle: dict) -> dict:
    # Si no es transaction/batch, lo envolvemos en transaction
    if bundle.get("resourceType") != "Bundle" or bundle.get("type") not in ("transaction", "batch"):
        tx = {"resourceType": "Bundle", "type": "transaction", "entry": []}
        for e in (bundle.get("entry") or []):
            r = e.get("resource")
            if isinstance(r, dict) and r.get("resourceType"):
                tx["entry"].append({
                    "resource": r,
                    "request": {"method": "POST", "url": r["resourceType"]}
                })
        bundle = tx

    headers = {"Content-Type": "application/fhir+json"}
    if HAPI_BEARER:
        headers["Authorization"] = f"Bearer {HAPI_BEARER}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(HAPI_BASE_URL, headers=headers, content=json.dumps(bundle))
        resp.raise_for_status()
        return resp.json()
    
def _new_job_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:8]}"

def _save_upload(f: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        shutil.copyfileobj(f.file, out)
    return dest

def _count_issues(outcome: dict):
    sev = {"fatal": 0, "error": 0, "warning": 0, "information": 0}
    for it in (outcome.get("issue") or []):
        s = (it.get("severity") or "").lower()
        if s in sev:
            sev[s] += 1
    return sev

async def _run_converter(input_path: Path, out_dir: Path) -> int:
    """
    Runs the external converter. It must create *.json (FHIR Bundles) inside out_dir.
    On failure, raises a RuntimeError with detailed diagnostics (exit code, duration, stderr/stdout tails).
    Also writes full logs to out_dir/_converter.stdout.log and out_dir/_converter.stderr.log.
    """
    if not CONVERTER_CMD:
        raise RuntimeError(
            "CONVERTER_CMD is not set. Define it via environment variable, e.g. "
            '"python path/to/transform.py --input {in} --outdir {out}".'
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = CONVERTER_CMD.replace("{in}", str(input_path)).replace("{out}", str(out_dir))

    start = time.time()
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    duration_ms = int((time.time() - start) * 1000)

    # Persist full logs for later inspection
    try:
        (out_dir / "_converter.stdout.log").write_bytes(stdout or b"")
        (out_dir / "_converter.stderr.log").write_bytes(stderr or b"")
    except Exception:
        pass

    def tail_bytes(b: bytes, n_lines: int = 30, limit: int = 8000) -> str:
        text = (b or b"").decode(errors="replace")
        tail = "\n".join(text.splitlines()[-n_lines:])
        return tail[-limit:]

    if proc.returncode != 0:
        err_msg = (
            f"Converter exited with code {proc.returncode}.\n"
            f"Command: {cmd}\n"
            f"DurationMs: {duration_ms}\n"
            f"Stderr (last 30 lines):\n{tail_bytes(stderr)}\n"
            f"Stdout (last 30 lines):\n{tail_bytes(stdout)}"
        )
        raise RuntimeError(err_msg)

    bundles = list(out_dir.glob("*.json"))
    return len(bundles)

async def _validate_bundle(client: httpx.AsyncClient, path: Path, profile: Optional[str]):
    params = {}
    if profile:
        params["profile"] = profile
    url = f"{VALIDATOR_BASE_URL}{VALIDATOR_PATH}"
    print(f"Validating {path} with {url}...")
    try:
        r = await client.post(url, params=params, content=path.read_bytes(),
                              headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return path, r.json()
    except httpx.HTTPError as e:
        return path, {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "fatal",
                "code": "exception",
                "diagnostics": f"Validator call failed: {e}"
            }]
        }

async def _validate_many(paths: List[Path], profile: Optional[str], concurrency: int):
    sem = asyncio.Semaphore(concurrency)
    timeout = httpx.Timeout(60.0, connect=10.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async def one(p: Path):
            async with sem:
                return await _validate_bundle(client, p, profile)
        return await asyncio.gather(*[one(p) for p in paths])

@app.get("/health")
def health():
    return {"status": "UP"}

@app.post("/jobs/csv", status_code=201)
async def create_job_from_csv(
    file: UploadFile = File(..., description="Input CSV file"),
    profile: Optional[str] = Form(None, description="Canonical profile to enforce (optional)"),
    parallelism: int = Form(6, ge=1, le=16, description="Validation parallelism"),
    persistToHapi: bool = Form(False, description="Persist validated resources into HAPI"),
    persistOnlyIfNoErrors: bool = Form(True, description="Only persist when there are no fatal/error issues"),
):
    """
    1) Store the CSV file
    2) Run your external converter (CONVERTER_CMD), which must generate Bundles *.json in out_dir
    3) Validate each Bundle against validator-api
    4) Return aggregated report
    """
    start = time.time()
    job_id = _new_job_id()
    job_dir = WORKDIR / "jobs" / job_id
    in_dir = job_dir / "input"
    out_dir = job_dir / "bundles"
    oo_dir = job_dir / "outcomes"
    for d in (in_dir, out_dir, oo_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1) guardar CSV
    original_name = file.filename or "input.csv"
    input_path = _save_upload(file, in_dir / original_name)

    # 2) ejecutar conversor
    try:
        n_bundles = await _run_converter(input_path, out_dir)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Conversion failed: {str(e)}"
        )

    paths = sorted(out_dir.glob("*.json"))
    if not paths:
        raise HTTPException(400, "The converter did not produce any Bundle (*.json)")

    # 3) validar
    results = await _validate_many(paths, profile=profile, concurrency=parallelism)

    totals = {"fatal": 0, "error": 0, "warning": 0, "information": 0}
    rows = []
    for p, outcome in results:
        # guarda el OperationOutcome
        (oo_dir / f"{p.stem}.oo.json").write_text(json.dumps(outcome, ensure_ascii=False), encoding="utf-8")
        sev = _count_issues(outcome)
        for k in totals: totals[k] += sev[k]
        rows.append({"bundle": p.name, "issues": sev})

    end = time.time()
    summary = {
        "jobId": job_id,
        "input": {"filename": original_name, "rows": None},
        "totals": {
            "bundles": len(paths),
            "errors": totals["fatal"] + totals["error"],
            "warnings": totals["warning"]
        },
        "bySeverity": totals,
        "startedAt": datetime.utcfromtimestamp(start).isoformat() + "Z",
        "finishedAt": datetime.utcfromtimestamp(end).isoformat() + "Z",
        "durationMs": int((end - start) * 1000),
        "bundles": rows
    }
    (job_dir / "job.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    hapi_upload = None
    if persistToHapi:
        if not HAPI_BASE_URL:
            hapi_upload = {"skipped": True, "reason": "HAPI_BASE_URL not configured"}
        else:
            errors_total = summary["totals"]["errors"]
            if persistOnlyIfNoErrors and errors_total > 0:
                hapi_upload = {"skipped": True, "reason": "errors_present", "errors": errors_total}
            else:
                ok = 0
                fails = []
                for p in paths:  # 'paths' ya tiene tus *.json generados por el conversor
                    try:
                        bundle = json.loads(p.read_text(encoding="utf-8"))
                        _tag_bundle(bundle, job_id)
                        await _post_transaction(bundle)
                        ok += 1
                    except Exception as e:
                        fails.append({"bundle": p.name, "error": str(e)[:500]})
                hapi_upload = {"attempted": len(paths), "uploaded": ok, "failures": fails}

    summary["hapiUpload"] = hapi_upload
    (job_dir / "job.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return JSONResponse(summary)

DEFAULT_RT = ["Condition", "Observation", "Procedure", "MedicationStatement", "Encounter", "Patient"]
