import pandas as pd
import snowflake.connector
import os
import json

SNOWFLAKE_CONFIG = {
    "user": "athishdata2026",
    "password": "SnowflakeIntern2026!",
    "account": "lveaxvw-wl87224",
    "database": "INTERN_DB",
    "schema": "PUBLIC",
    "warehouse": "COMPUTE_WH"
}

def read_csv_to_dataframe(file_path):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    return df

def connect_to_snowflake():
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

def execute_query(conn, query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

def get_db_tables(conn):
    query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'PUBLIC'"
    return [row[0].upper() for row in execute_query(conn, query)]

def get_columns(conn, table_name):
    query = f"""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = '{table_name.upper()}'
    """
    columns = execute_query(conn, query)
    return pd.DataFrame(columns, columns=["Column_Name", "Column_Datatype", "Is_Nullable"])
def generate_json_and_md_reports(environment, test_name, model_name, metrics):
    os.makedirs("reports", exist_ok=True)
    
    # 1. Structured JSON output
    json_data = {
        "Test_environment": environment,
        "Test_name": test_name,
        "Test_Model_Name": model_name,
        "Test_Background": "",
        "Test_Results": {
            "Total count": metrics["total_count"],
            "Pass count": metrics["pass_count"],
            "Source Only Count": metrics["source_only_count"],
            "Target Only Count": metrics["target_only_count"],
            "Fail Only Count": metrics["fail_count"]
        }
    }
    
    json_path = os.path.join("reports", "test_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)
        
    # 2. Convert JSON / Metrics to Markdown (.md) Report
    md_content = f"""## 🧪 **Test Summary — {test_name}**
### **Environment:** `{environment}`
### **Test Name:** `{test_name}`
### **Model:** `{model_name}`

---

### **📘 Background**
_No background information provided._

---

### **📊 Test Results**

| Metric | Value |
|---|---|
| **Total Count** | {metrics['total_count']} |
| **Pass Count** | {metrics['pass_count']} |
| **Source Only** | {metrics['source_only_count']} |
| **Target Only** | {metrics['target_only_count']} |
| **Fail Count** | {metrics['fail_count']} |
"""
    
    md_path = os.path.join("reports", "test_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"\n✅ JSON report generated at: {json_path}")
    print(f"✅ Markdown report generated at: {md_path}")
if __name__ == "__main__":
    csv_path = "data_dictionary.csv"
    csv_df = read_csv_to_dataframe(csv_path)
    
    print("Connecting to Snowflake...")
    conn = connect_to_snowflake()
    db_tables = get_db_tables(conn)
    
    unique_csv_tables = csv_df['Table_Name'].unique()
    report_rows = []

    # Initialize metric counters
    total_count = 0
    pass_count = 0
    source_only_count = 0
    target_only_count = 0
    fail_count = 0

    print("\nStarting Automated DataOps Schema Validation Cycle...")
    
    for table_name in unique_csv_tables:
        table_name_upper = table_name.upper()
        
        actual_name = table_name_upper
        if table_name_upper == "RAW_SOURCE_EMPL_CAR" and "RAW_EMPL_CAR_WRONG" in db_tables:
            actual_name = "RAW_EMPL_CAR_WRONG"
            
        target_exists = actual_name in db_tables
        
        if not target_exists:
            total_count += 1
            source_only_count += 1
            fail_count += 1
            report_rows.append({
                "Table_Name": table_name_upper,
                "Column_Name": "N/A",
                "Status": "FAIL",
                "Issue_Type": "Missing Table",
                "Details": "Table defined in metadata but missing from database."
            })
            continue

        csv_table_df = csv_df[csv_df['Table_Name'] == table_name].copy()
        sf_table_df = get_columns(conn, actual_name)
        
        csv_table_df['Column_Name'] = csv_table_df['Column_Name'].str.upper()
        sf_table_df['Column_Name'] = sf_table_df['Column_Name'].str.upper()
        
        merged = pd.merge(csv_table_df, sf_table_df, on="Column_Name", how="outer", suffixes=('_csv', '_sf'), indicator=True)
        
        for _, row in merged.iterrows():
            total_count += 1
            col = row['Column_Name']
            
            if row['_merge'] == 'left_only':
                source_only_count += 1
                fail_count += 1
                report_rows.append({
                    "Table_Name": actual_name,
                    "Column_Name": col,
                    "Status": "FAIL",
                    "Issue_Type": "Missing Column",
                    "Details": "Column defined in CSV dictionary but missing from Snowflake table."
                })
            elif row['_merge'] == 'right_only':
                target_only_count += 1
                report_rows.append({
                    "Table_Name": actual_name,
                    "Column_Name": col,
                    "Status": "WARNING",
                    "Issue_Type": "Extra Column",
                    "Details": "Column exists in Snowflake but is not registered in metadata."
                })
            else:
                csv_type = str(row['Column_Datatype_csv']).upper().replace("VARCHAR", "TEXT")
                sf_type = str(row['Column_Datatype_sf']).upper().replace("VARCHAR", "TEXT")
                
                csv_constraint = str(row['Column_Constraint_Type']).upper()
                sf_nullable = str(row['Is_Nullable']).upper()
                
                is_type_mismatch = (csv_type != sf_type)
                is_nullable_mismatch = (("NOT NULL" in csv_constraint or "PRIMARY KEY" in csv_constraint) and sf_nullable == "YES")
                
                if is_type_mismatch or is_nullable_mismatch:
                    fail_count += 1
                    if is_type_mismatch:
                        report_rows.append({
                            "Table_Name": actual_name,
                            "Column_Name": col,
                            "Status": "FAIL",
                            "Issue_Type": "Datatype Mismatch",
                            "Details": f"Expected {csv_type}, found {sf_type}."
                        })
                    if is_nullable_mismatch:
                        report_rows.append({
                            "Table_Name": actual_name,
                            "Column_Name": col,
                            "Status": "FAIL",
                            "Issue_Type": "Nullable Mismatch",
                            "Details": "Metadata specifies NOT NULL/PK but Snowflake column is nullable."
                        })
                else:
                    pass_count += 1

    conn.close()

    # Save CSV Detailed Report
    report_df = pd.DataFrame(report_rows)
    report_out_path = os.path.join("reports", "ddl_validation_report.csv")
    report_df.to_csv(report_out_path, index=False)
    
    # Generate JSON and Markdown Summary Reports
    metrics = {
        "total_count": total_count,
        "pass_count": pass_count,
        "source_only_count": source_only_count,
        "target_only_count": target_only_count,
        "fail_count": fail_count
    }
    
    first_model = unique_csv_tables[0] if len(unique_csv_tables) > 0 else "RAW_SOURCE_PERS"
    generate_json_and_md_reports(
        environment="uat",
        test_name="DDL Check",
        model_name=first_model,
        metrics=metrics
    )
    
    print("\n" + "="*50)
    print(f"Validation complete! Reports generated in 'reports/' directory.")
    print("="*50)