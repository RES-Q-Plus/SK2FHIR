from typing import List
from pyspark.sql.functions import col, create_map, lit, when
from itertools import chain

from typing import Any, Dict, Optional
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def mapping(
    df: DataFrame,
    source_col: str,
    lookup: Dict[Any, Any],
    target_col: Optional[str] = None,
    drop_unmapped: bool = False,
    default: Optional[Any] = None,   # valor por defecto cuando no hay match o falta la source
    strict: bool = False             # si True, lanza error si falta la source
) -> DataFrame:
    """
    Maps df[source_col] -> df[target_col] using lookup (dict).
    - Creates target_col if it didn't exist.
    - If source_col is missing:
        - strict=True -> raises error
        - strict=False -> creates target_col with `default` (or NULL if default=None)
    - If the source value is not in lookup -> NULL (or `default` if specified).
    """
    tgt = target_col or source_col

    # 1) If source column is missing
    if source_col not in df.columns:
        if strict:
            raise ValueError(f"mapping(): columna fuente '{source_col}' no existe en el DataFrame")
        fill = F.lit(default) if default is not None else F.lit(None)
        return df.withColumn(tgt, fill)

    # 2) Build the map with keys as string (to match cast("string"))
    #    If the dict values are Enums/objects, pass .value or str/int.
    flat = []

    for k, v in lookup.items():
        flat.extend([F.lit(str(k)), F.lit(v)])
    mapping_expr = F.create_map(*flat)

    # 3) Secure lookup
    key = F.col(source_col).cast("string")
    looked_up = mapping_expr.getItem(key) 
    # 4) Apply default if needed
    value = F.coalesce(looked_up, F.lit(default)) if default is not None else looked_up
    out = df.withColumn(tgt, value)

    # 5) Filter unmapped if requested
    if drop_unmapped:
        out = out.filter(F.col(tgt).isNotNull())

    return out


from functools import reduce
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, create_map, lit, coalesce
from itertools import chain


def minute_difference(
    df: DataFrame,
    target_col: str,
    start_col: str,
    end_col: str
) -> DataFrame:

    """
    Calculates the difference in minutes between two timestamp columns.
    Parameters:
    - df: Spark DataFrame with the timestamp columns.
    - target_col: Name of the output column to store the difference in minutes.
    - start_col: Name of the start timestamp column.
    - end_col: Name of the end timestamp column.

    Returns:
    - New DataFrame with the target_col added or replaced.
    """
    return df.withColumn(
        target_col,
        ((col(end_col).cast("long") - col(start_col).cast("long")) / 60).cast("integer")
    )


from typing import List
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def disjuction(
    df: DataFrame,
    target_col: str,
    source_cols: List[str]
) -> DataFrame:

    """
        Builds or updates target_col as the logical disjunction (OR) row by row of several columns.
        - If any column in source_cols is True → target_col = True.
        - If all are False or null → target_col = False.
        - If source_cols is empty → target_col = False.
        Parameters:
        - df: Spark DataFrame.
        - target_col: Name of the output boolean column.
        - source_cols: List of source boolean columns to disjoin.
        Returns:
        - New DataFrame with target_col added or updated.
    """
    exprs = [
        F.coalesce(F.col(c).cast("boolean"), F.lit(False))
        for c in source_cols if c in df.columns
    ]

    if not exprs:
        boolean_expr = F.lit(False)
    else:
        # OR acumulado de todas las expresiones
        boolean_expr = exprs[0]
        for e in exprs[1:]:
            boolean_expr = boolean_expr | e

    return df.withColumn(target_col, boolean_expr)

def cast_types(
    df: DataFrame,
    spark_type: str,
    columns: list[str]
) -> DataFrame:

    """
    Casts multiple columns to a specified Spark type (e.g., 'int', 'float', 'string', 'boolean').
    Parameters:
    - df: Spark DataFrame.
    - spark_type: Name of the Spark type to cast to ("int", "long", "float", "boolean", etc.).
    - columns: List of columns to cast.
    Returns:
    - New DataFrame with the columns casted.
    """
    for c in columns:
        df = df.withColumn(c, col(c).cast(spark_type))
    return df


def remove_values(
    df: DataFrame,
    column: str,
    invalid_ranges: list[range]
) -> DataFrame:
    """
    Replaces with null the values in `column` that fall within any
    of the ranges in `invalid_ranges`.
    """
    # Construir condición para valores inválidos
    invalid_cond = None
    for r in invalid_ranges:
        cond = col(column).between(r.start, r.stop - 1)
        invalid_cond = cond if invalid_cond is None else (invalid_cond | cond)
    if invalid_cond is None:
        return df
    # Asigna null cuando la condición se cumple
    return df.withColumn(
        column,
        when(invalid_cond, None).otherwise(col(column))
    )