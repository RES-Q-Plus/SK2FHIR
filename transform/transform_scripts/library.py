import unicodedata
from pandas import DataFrame
from functools import reduce
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, create_map, lit, when
from pyspark.sql.functions import to_timestamp as spark_to_timestamp, date_format
from itertools import chain

def norm(s):
    # Normalice accents, remove BOM, NBSP and extra spaces
    s = unicodedata.normalize("NFC", s)
    return s.replace('\ufeff', '').replace('\xa0', ' ').strip()

def rename_dataframe_columns(df, columns_map):
    real_by_norm = {norm(c): c for c in df.columns}
    renamed = df
    for old_raw, new_name in columns_map.items():
        key = norm(old_raw)
        if key in real_by_norm:
            real = real_by_norm[key]
            renamed = renamed.withColumnRenamed(real, new_name)
        else:
            import difflib
            suggestion = difflib.get_close_matches(key, real_by_norm.keys(), n=1)
    return renamed




def substring(col, pos, length):
    """ Extracts a substring from a column.
    """
    return col.substr(pos, length)

def to_timestamp(
    df: DataFrame,
    column: str,
    fmt: str = 'M/d/yyyy H:mm'
) -> DataFrame:
 
    """
    Transforms a string column to TimestampType in Spark.
    Parameters:
    - df: Spark DataFrame.
    - column: Name of the string column with date and time.
    - fmt: Input timestamp format.
    Returns:
    - DataFrame with the column converted to TimestampType.
    """
    return df.withColumn(column, spark_to_timestamp(col(column), fmt))


def to_time(
    df: DataFrame,
    column: str,
    fmt: str = 'H:mm'
) -> DataFrame:

    """
    Extracts the time part from a string time column in Spark.
    Parameters:
    - df: Spark DataFrame.
    - column: Name of the string column with time.
    - fmt: Input time format.
    Returns:
    - DataFrame with the column converted to string 'HH:mm:ss'.
    """
    # Convierte a timestamp primero, luego formatea sólo la hora
    temp_col = f"_{column}_ts"
    df = df.withColumn(temp_col, spark_to_timestamp(col(column), fmt))
    df = df.withColumn(column, date_format(col(temp_col), 'HH:mm:ss'))
    return df.drop(temp_col)