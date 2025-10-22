FHIR INFRASTRUCTURE WITH SNOWSTORM + HAPI FHIR + VALIDATOR + ORCHESTRATOR
=========================================================================

This repository provides a complete containerized environment for working with FHIR and SNOMED CT terminology.  
It includes the following key components:

- Snowstorm (SNOMED CT terminology server) powered by Elasticsearch (http://localhost:8081/swagger-ui/index.html)
- FHIR Validator API (R5) (http://localhost:8085/swagger-ui/index.html)
- HAPI FHIR Server (R5) with PostgreSQL backend 
- Orchestrator API (FastAPI) to convert CSV → FHIR Bundles → validate → (optionally) persist into HAPI (http://localhost:8090/docs#/default)

------------------------------------------------------------
# 1. OVERVIEW
------------------------------------------------------------

| Service          | Role / Function                                 | Port  | Depends On      |
|------------------|--------------------------------------------------|-------|-----------------|
| Elasticsearch    | Search backend for Snowstorm                     | 9200  | —               |
| Snowstorm        | SNOMED CT terminology server (FHIR interface)    | 8081  | Elasticsearch   |
| Validator        | FHIR Validator API (R5)                          | 8085  | Snowstorm       |
| PostgreSQL (db)  | Database for HAPI FHIR                           | 5432  | —               |
| HAPI FHIR Server | Main FHIR repository (R5)                        | 8082  | PostgreSQL      |
| Orchestrator API | CSV → FHIR transformation, validation, upload    | 8090  | Validator, HAPI |

------------------------------------------------------------
# 2. STARTING THE STACK
------------------------------------------------------------

Run the entire stack:
    docker compose up -d

Check that all services are running:
    docker ps

Quick health checks:
    Snowstorm FHIR:  http://localhost:8081/fhir/metadata
    Validator API:   http://localhost:8085/actuator/health
    HAPI FHIR:       http://localhost:8082/fhir/metadata
    Orchestrator:    http://localhost:8090/health

------------------------------------------------------------
# 3. ORCHESTRATOR API (FASTAPI)
------------------------------------------------------------

The Orchestrator coordinates conversion, validation, and optional persistence of FHIR data.  
Its behavior is configured via environment variables.

Main environment variables:

    WORKDIR             Default: /app/workdir
    VALIDATOR_BASE_URL  Default: http://validator:8080
    VALIDATOR_PATH      Default: /api/validate/bundle
    HAPI_BASE_URL       e.g., http://hapi:8080/fhir (optional)
    HAPI_BEARER         Optional Bearer token for HAPI uploads
    JOB_TAG_SYSTEM      Default: https://sk_fhir/job
    CONVERTER_CMD       REQUIRED: command to execute your converter script

The converter command MUST use placeholders:
    {in}  = path to input CSV
    {out} = directory where JSON FHIR Bundles will be generated

Examples:

    spark-submit --master local[*] /app/transform/transform_scripts/transform.py --input {in} --outdir {out}
    python /app/transform/transform_scripts/transform.py --input {in} --outdir {out}

The converter must generate one or more *.json FHIR Bundles inside {out}.

------------------------------------------------------------
# 4. API ENDPOINTS
------------------------------------------------------------

## 4.1 Health Check
----------------
GET /health  
Response:
    { "status": "UP" }

## 4.2 Create Job from CSV
-----------------------
POST /jobs/csv  
Content-Type: multipart/form-data

Form fields:
    file:                (required) input CSV file
    profile:             (optional) canonical profile URL to validate against
    parallelism:         (int, 1–16, default=6) number of concurrent validations
    persistToHapi:       (bool, default=false) if true, upload bundles to HAPI
    persistOnlyIfNoErrors: (bool, default=true) upload only if no fatal/error issues

------------------------------------------------------------
# 5. CURL EXAMPLES
------------------------------------------------------------

A) Validate only (no persistence)
---------------------------------
curl -fS -X POST "http://localhost:8090/jobs/csv" \
  -F "file=@/path/to/dataset.csv;type=text/csv" \
  -F "parallelism=6" \
  -F "persistToHapi=false"

B) Validate against a canonical FHIR profile
--------------------------------------------
curl -fS -X POST "http://localhost:8090/jobs/csv" \
  -F "file=@/path/to/dataset.csv;type=text/csv" \
  -F "profile=https://hl7.org/fhir/StructureDefinition/Patient" \
  -F "persistToHapi=false"

C) Validate and persist to HAPI (only if no errors)
---------------------------------------------------
# HAPI_BASE_URL must be set in orchestrator-api container.
curl -fS -X POST "http://localhost:8090/jobs/csv" \
  -F "file=@/path/to/dataset.csv;type=text/csv" \
  -F "persistToHapi=true" \
  -F "persistOnlyIfNoErrors=true"

D) Force persistence even with validation errors (not recommended)
------------------------------------------------------------------
curl -fS -X POST "http://localhost:8090/jobs/csv" \
  -F "file=@/path/to/dataset.csv;type=text/csv" \
  -F "persistToHapi=true" \
  -F "persistOnlyIfNoErrors=false"

------------------------------------------------------------
# 6. INTERNAL WORKFLOW
------------------------------------------------------------

1. The CSV file is uploaded and saved to:
       WORKDIR/jobs/<jobId>/input/
2. The external converter is executed using CONVERTER_CMD.
   It must produce one or more JSON FHIR Bundles in:
       WORKDIR/jobs/<jobId>/bundles/
3. Each Bundle is validated against:
       VALIDATOR_BASE_URL + VALIDATOR_PATH
   Validation runs concurrently according to the `parallelism` value.
4. OperationOutcomes are stored under:
       WORKDIR/jobs/<jobId>/outcomes/
5. A summary file "job.json" is generated with global statistics:
       WORKDIR/jobs/<jobId>/job.json
6. (Optional) If persistToHapi=true and conditions are met,
   Bundles are uploaded to the configured HAPI FHIR server.

------------------------------------------------------------
# 7. JOB OUTPUT STRUCTURE
------------------------------------------------------------

Each job produces the following directory tree:

WORKDIR/jobs/<jobId>/
├── input/            # original uploaded CSV
├── bundles/          # generated FHIR Bundles (*.json)
├── outcomes/         # validation OperationOutcomes (*.oo.json)
└── job.json          # aggregated summary report

The job.json file includes:
- Total bundles processed
- Count of errors, warnings, and info issues
- Execution duration (ms)
- Optional HAPI upload results

------------------------------------------------------------
# 8. CLEANUP
------------------------------------------------------------

To stop and remove all containers and volumes:
    docker compose down -v

------------------------------------------------------------
# 9. LICENSE
------------------------------------------------------------

This project is distributed under the MIT License,  
except for external base images (HAPI, Snowstorm, etc.)  
which retain their respective licenses.

------------------------------------------------------------
# 10. SYSTEM FLOW (SUMMARY)
------------------------------------------------------------

CSV → Orchestrator API → Converter Script → Validator API →  
→ Snowstorm Terminology (SNOMED) → (optional) HAPI FHIR → PostgreSQL


