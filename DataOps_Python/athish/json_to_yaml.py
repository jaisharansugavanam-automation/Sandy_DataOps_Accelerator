import json
import os
import pandas as pd
import yaml

# Ensure PyYAML dumps multiline strings cleanly without unnecessary escaping
def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)


def read_test_metadata(metadata_json_path: str) -> dict:
    """Reads and parses the JSON test metadata file."""
    if not os.path.exists(metadata_json_path):
        raise FileNotFoundError(f"Metadata JSON not found at: {metadata_json_path}")
    
    with open(metadata_json_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {metadata_json_path}: {str(e)}")


def read_test_reference(test_reference_csv_path: str) -> pd.DataFrame:
    """Reads the reference CSV catalogue containing dbt test templates."""
    if not os.path.exists(test_reference_csv_path):
        raise FileNotFoundError(f"Reference CSV not found at: {test_reference_csv_path}")
    
    df = pd.read_csv(test_reference_csv_path)
    # Standardize test names for matching
    df['clean_test_name'] = df['Test Case Name'].astype(str).str.strip().str.lower()
    return df


def find_test_template(test_type: str, reference_df: pd.DataFrame) -> dict:
    """Looks up a test in the reference CSV and parses its template string into Python data."""
    clean_requested = test_type.strip().lower()
    match = reference_df[reference_df['clean_test_name'] == clean_requested]

    if match.empty:
        raise ValueError(f"FAIL – Test template not found in reference CSV for test_type: '{test_type}'")

    raw_template_str = match.iloc[0]['Test Structure']
    
    try:
        parsed_template = yaml.safe_load(raw_template_str)
        return parsed_template
    except Exception as e:
        raise ValueError(f"Failed to parse YAML template string in reference CSV for '{test_type}': {str(e)}")


def populate_template(template, context: dict):
    """Recursively replaces placeholder strings like {column_name} or {table_name}."""
    if isinstance(template, str):
        for key, val in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in template:
                template = template.replace(placeholder, str(val))
        return template
    elif isinstance(template, dict):
        return {k: populate_template(v, context) for k, v in template.items()}
    elif isinstance(template, list):
        return [populate_template(item, context) for item in template]
    return template


def build_dbt_yaml_structure(metadata: dict, reference_df: pd.DataFrame) -> dict:
    """Combines table-level and column-level tests into standard dbt YAML hierarchy."""
    table_name = metadata.get("table_name")
    if not table_name:
        raise KeyError("Metadata JSON is missing the required 'table_name' root field.")

    model_entry = {"name": table_name}

    # 1. Process Table-Level Tests
    table_tests_req = metadata.get("table_tests", [])
    if table_tests_req:
        model_entry["tests"] = []
        for t_req in table_tests_req:
            test_type = t_req.get("test_type")
            template = find_test_template(test_type, reference_df)
            context = {**t_req, "table_name": table_name}
            populated = populate_template(template, context)
            model_entry["tests"].append(populated)

    # 2. Process Column-Level Tests
    column_tests_req = metadata.get("column_tests", [])
    if column_tests_req:
        columns_dict = {}
        for c_req in column_tests_req:
            col_name = c_req.get("column_name")
            if not col_name:
                raise KeyError(f"Column test request missing 'column_name': {c_req}")

            test_type = c_req.get("test_type")
            template = find_test_template(test_type, reference_df)
            
            context = {**c_req, "table_name": table_name, "column_name": col_name}
            populated = populate_template(template, context)

            if col_name not in columns_dict:
                columns_dict[col_name] = []
            columns_dict[col_name].append(populated)

        model_entry["columns"] = [
            {"name": col, "tests": tests_list}
            for col, tests_list in columns_dict.items()
        ]

    return {
        "version": 2,
        "models": [model_entry]
    }


def generate_dbt_test_yaml(metadata_json_path: str, test_reference_csv_path: str, output_yaml_path: str):
    """Main orchestration function to read inputs, build YAML structure, and write out file."""
    # Step 1: Read input files
    metadata = read_test_metadata(metadata_json_path)
    reference_df = read_test_reference(test_reference_csv_path)

    # Step 2: Build internal dict hierarchy
    yaml_structure = build_dbt_yaml_structure(metadata, reference_df)

    # Step 3: Write to YAML file
    with open(output_yaml_path, 'w') as f:
        yaml.dump(yaml_structure, f, sort_keys=False, default_flow_style=False)

    print(f"Successfully generated dbt test YAML: {output_yaml_path}")


# Execution example for direct running
if __name__ == "__main__":
    generate_dbt_test_yaml(
        metadata_json_path="test_metadata.json",
        test_reference_csv_path="test_reference.csv",
        output_yaml_path="RAW_SOURCE_EMPL_ACC_tests.yml"
    )