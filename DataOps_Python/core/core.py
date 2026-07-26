# ============================================================
# File       : core.py
# Folder     : DataOps_Python/core/
# Version    : 1.0.0
# Purpose    : Central library of reusable Python utility functions
#              for the Sandy Enterprise DataOps Accelerator framework.
#              All features — testing, metadata, orchestration, publishing —
#              import from this module. Functions are grouped by domain category.
#
# Categories :
#   [1] Snowflake   — connect, execute SQL, return DataFrames, information schema
#   [2] CSV         — read/write CSV, Excel → CSV → DataFrame conversions
#
# Principles : One function, one responsibility.
#              No hardcoded credentials — all config passed via args or env vars.
#              All functions return typed, predictable outputs.
#
# Created    : 2026-07-19
# Author     : Sandy DataOps
# ============================================================

import os
import json
import pandas as pd

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


# ============================================================
# [1] SNOWFLAKE FUNCTIONS
# ============================================================

def get_snowflake_connection(
    account: str = None,
    user: str = None,
    password: str = None,
    warehouse: str = None,
    database: str = None,
    schema: str = None,
    role: str = None,
):
    """
    Create and return a Snowflake connection using snowflake-connector-python.
    Falls back to environment variables if parameters are not passed.

    Returns:
        snowflake.connector.SnowflakeConnection
    """
    import snowflake.connector

    return snowflake.connector.connect(
        account=account or os.environ["SNOWFLAKE_ACCOUNT"],
        user=user or os.environ["SNOWFLAKE_USER"],
        password=password or os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=warehouse or os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=database or os.environ.get("SNOWFLAKE_DATABASE"),
        schema=schema or os.environ.get("SNOWFLAKE_SCHEMA"),
        role=role or os.environ.get("SNOWFLAKE_ROLE"),
    )


def snowflake_query_to_df(sql: str, conn=None, **conn_kwargs) -> pd.DataFrame:
    """
    Execute a SQL query against Snowflake and return the result as a DataFrame.

    Args:
        sql        : SQL string to execute.
        conn       : Optional existing Snowflake connection. Created if not passed.
        **conn_kwargs: Passed to get_snowflake_connection() if conn is None.

    Returns:
        pd.DataFrame
    """
    from snowflake.connector.pandas_tools import pd_writer

    close_after = conn is None
    if conn is None:
        conn = get_snowflake_connection(**conn_kwargs)

    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        df = cursor.fetch_pandas_all()
        return df
    finally:
        cursor.close()
        if close_after:
            conn.close()


def get_information_schema_columns(
    database: str,
    schema: str,
    table: str = None,
    conn=None,
    **conn_kwargs,
) -> pd.DataFrame:
    """
    Retrieve column metadata from Snowflake INFORMATION_SCHEMA.COLUMNS.

    Args:
        database : Target Snowflake database.
        schema   : Target schema name.
        table    : Optional — filter to a specific table. Returns all tables if None.
        conn     : Optional existing Snowflake connection.

    Returns:
        pd.DataFrame with columns: TABLE_NAME, COLUMN_NAME, DATA_TYPE,
                                   IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH,
                                   NUMERIC_PRECISION, ORDINAL_POSITION
    """
    table_filter = f"AND TABLE_NAME = UPPER('{table}')" if table else ""
    sql = f"""
        SELECT
            TABLE_CATALOG,
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            ORDINAL_POSITION,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            NUMERIC_PRECISION,
            IS_NULLABLE
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = UPPER('{schema}')
        {table_filter}
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """
    return snowflake_query_to_df(sql, conn=conn, **conn_kwargs)


def get_information_schema_tables(
    database: str,
    schema: str = None,
    conn=None,
    **conn_kwargs,
) -> pd.DataFrame:
    """
    Retrieve table metadata from Snowflake INFORMATION_SCHEMA.TABLES.

    Args:
        database : Target Snowflake database.
        schema   : Optional — filter to a specific schema.
        conn     : Optional existing Snowflake connection.

    Returns:
        pd.DataFrame with table names, row counts, creation times, etc.
    """
    schema_filter = f"AND TABLE_SCHEMA = UPPER('{schema}')" if schema else ""
    sql = f"""
        SELECT
            TABLE_CATALOG,
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE,
            ROW_COUNT,
            BYTES,
            CREATED,
            LAST_ALTERED
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        {schema_filter}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    return snowflake_query_to_df(sql, conn=conn, **conn_kwargs)


# ============================================================
# [2] CSV FUNCTIONS
# ============================================================

def read_csv(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Read a CSV file into a pandas DataFrame.

    Args:
        file_path : Path to the CSV file.
        **kwargs  : Additional arguments passed to pd.read_csv().

    Returns:
        pd.DataFrame
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return pd.read_csv(path, **kwargs)


def write_csv(df: pd.DataFrame, file_path: str, index: bool = False, **kwargs) -> str:
    """
    Write a pandas DataFrame to a CSV file.

    Args:
        df        : DataFrame to write.
        file_path : Destination path for the CSV file.
        index     : Whether to write row index. Default False.
        **kwargs  : Additional arguments passed to df.to_csv().

    Returns:
        str: Absolute path of the written file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, **kwargs)
    return str(path.resolve())


def excel_to_df(file_path: str, sheet_name=0, **kwargs) -> pd.DataFrame:
    """
    Read an Excel file (.xlsx / .xls) into a pandas DataFrame.

    Args:
        file_path  : Path to the Excel file.
        sheet_name : Sheet name or index. Default 0 (first sheet).
        **kwargs   : Additional arguments passed to pd.read_excel().

    Returns:
        pd.DataFrame
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    return pd.read_excel(path, sheet_name=sheet_name, **kwargs)


def excel_to_csv(file_path: str, output_path: str, sheet_name=0, index: bool = False) -> str:
    """
    Convert an Excel file to a CSV file.

    Args:
        file_path   : Path to the source Excel file.
        output_path : Destination path for the output CSV.
        sheet_name  : Sheet name or index. Default 0.
        index       : Whether to include row index in output. Default False.

    Returns:
        str: Absolute path of the written CSV file.
    """
    df = excel_to_df(file_path, sheet_name=sheet_name)
    return write_csv(df, output_path, index=index)


def df_to_csv(df: pd.DataFrame, file_path: str, index: bool = False) -> str:
    """
    Alias for write_csv. Converts a DataFrame to a CSV file.

    Args:
        df        : Source DataFrame.
        file_path : Destination CSV path.
        index     : Whether to include row index. Default False.

    Returns:
        str: Absolute path of the written file.
    """
    return write_csv(df, file_path, index=index)


def csv_to_df(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Alias for read_csv. Reads a CSV file into a DataFrame.

    Args:
        file_path : Path to the CSV file.
        **kwargs  : Additional arguments passed to pd.read_csv().

    Returns:
        pd.DataFrame
    """
    return read_csv(file_path, **kwargs)
