# -*- coding: utf-8 -*-
"""
Uso:
  spark-submit --master local[*] transform.py --input <CSV> --outdir <CARPETA> --sep ';' --absolute-base https://mi-fhir/base

Contrato:
- Lee el CSV (Spark), aplica:
    df -> rename_dataframe_columns(df, column_mapping)
    df -> transformation(df)
- Por cada fila resultante, llama transform_to_fhir(row_dict) y escribe
  UN Bundle por archivo JSON dentro de --outdir (bundle_00000.json, ...).
- Garantiza fullUrl válido (urn:uuid:... en minúsculas o absoluto si pasas --absolute-base).
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from data_modeling import transform_to_fhir
from library import rename_dataframe_columns
from pyspark.sql import SparkSession
from rename_columns import column_mapping
from preprocess import transformation
from fhir.resources.bundle import Bundle, BundleEntry

# ---------- utilidades ----------

def log(msg: str):
    print(msg, flush=True)

def ensure_fullurls(bundle: Bundle, absolute_base: str | None) -> Bundle:

    """
    Ensures that each entry has a valid fullUrl:
    - If you pass --absolute-base: http(s)://.../ResourceType/id
    - If not: urn:uuid:<hex_lower>
    Also forces lowercase UUIDs.
    """
    
    entries = bundle.entry or []
    for e in entries:
        e = dict(e)
        res = e.get("resource", {}) or {}
        rtype = res.get("resourceType")
        rid = res.get("id")
        fu = e.get("fullUrl")

        # id por si acaso
        if not rid:
            rid = uuid.uuid4().hex  # minúsculas
            res["id"] = rid

        ok = False
        if isinstance(fu, str):
            if fu.startswith("urn:uuid:"):
                # normalizamos a minúsculas por si acaso
                try:
                    u = fu.split("urn:uuid:", 1)[1]
                    e["fullUrl"] = f"urn:uuid:{u.lower()}"
                    ok = True
                except Exception:
                    pass
            elif fu.startswith("http://") or fu.startswith("https://"):
                ok = True

        if not ok:
            if absolute_base and rtype and rid:
                e["fullUrl"] = f"{absolute_base.rstrip('/')}/{rtype}/{rid}"
            else:
                e["fullUrl"] = f"urn:uuid:{uuid.uuid4().hex}"  # hex ya es minúscula

        # reinyecta por si modificamos res
        e["resource"] = res
    bundle.entry = entries
    return bundle

def bundle_to_dict(bundle_obj) -> dict:
    """
        Supports:
        - pydantic objects (fhir.resources.*) → .model_dump(by_alias=True)
        - objects with .dict()/ .json()
        - already-dict
        - str JSON
    """
    if bundle_obj is None:
        raise ValueError("transform_to_fhir did not return a valid Bundle (None)")
    # pydantic v2
    if hasattr(bundle_obj, "model_dump"):
        return bundle_obj.model_dump(by_alias=True)
    # pydantic v1
    if hasattr(bundle_obj, "dict"):
        try:
            return bundle_obj.dict(by_alias=True)
        except TypeError:
            return bundle_obj.dict()
    # tiene .json()
    if hasattr(bundle_obj, "json"):
        return json.loads(bundle_obj.json())
    # ya es dict
    if isinstance(bundle_obj, dict):
        return bundle_obj
    # es cadena JSON
    if isinstance(bundle_obj, str):
        return json.loads(bundle_obj)
    raise TypeError(f"Cannot serialize the type returned by transform_to_fhir: {type(bundle_obj)}")

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input CSV file")
    ap.add_argument("--outdir", required=True, help="Directory to write output Bundles .json")
    ap.add_argument("--sep", default=";", help="CSV separator (default ';')")
    ap.add_argument("--absolute-base", default=None,
                    help="Absolute base for fullUrl (optional). If not provided, urn:uuid:... is used")
    ap.add_argument("--repartition", type=int, default=None,
                    help="Repartitions for parallelism (optional)")
    ap.add_argument("--limit", type=int, default=None,
                    help="Process only N rows (debug)")
    args = ap.parse_args()

    csv_path = Path(args.input)
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        log(f"❌ No existe el fichero de entrada: {csv_path}")
        sys.exit(2)

    log("▶️  Iniciando Spark…")
    spark = SparkSession.builder \
        .appName("csv-to-fhir-bundles") \
        .master("local[*]") \
        .getOrCreate()

    log(f"🔗 Spark UI: {spark.sparkContext.uiWebUrl}")

    log("▶️  Leyendo CSV…")
    df = spark.read.csv(str(csv_path), header=True, inferSchema=True, sep=args.sep)

    log("▶️  Renaming columns…")
    df = rename_dataframe_columns(df, column_mapping)
    log("▶️  Applying business transformation…")
    df = transformation(df)
    print(df)
    if args.repartition and args.repartition > 0:
        df = df.repartition(args.repartition)

    if args.limit and args.limit > 0:
        df = df.limit(args.limit)

    log("▶️  Generating Bundles…")
    count = 0

    # Streaming iteration to avoid driver memory overflow
    for row in df.toLocalIterator():
        row_dict = row.asDict(recursive=True)

        bundle_obj = transform_to_fhir(row_dict)
        
        if bundle_obj.get_resource_type() != "Bundle":
            raise ValueError("transform_to_fhir did not return a Bundle (resourceType != 'Bundle')")

        # Write file
        out_path = out_dir / f"bundle_{count:05d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(bundle_obj.json(indent=2, by_alias=True))
        count += 1
        if count % 100 == 0:
            log(f"   ... {count} bundles")

    log(f"✅ Done. Bundles written: {count} in {out_dir}")
    spark.stop()

if __name__ == "__main__":
    # Prints environment variables, useful when running on Windows or inside Docker
    print("JAVA_HOME:", os.environ.get("JAVA_HOME"))
    print("SPARK_HOME:", os.environ.get("SPARK_HOME"))
    print("HADOOP_HOME:", os.environ.get("HADOOP_HOME"))
    main()
