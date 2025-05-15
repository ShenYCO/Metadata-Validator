from pydantic import BaseModel, RootModel, field_validator, model_validator, ValidationError
from typing import List, Dict, Optional, Union
import re
import yaml
import os
from pathlib import Path
import traceback

# Reserved keywords and utility function
RESERVED_NAMES = {"select", "from", "where", "and", "or", "join"}

def is_valid_column_name(name: str) -> bool:
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))

# Load the schema file and extract column names
def load_schema(schema_path: str) -> Dict[str, List[str]]:
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)
    subject_area = schema.get("subject_area")
    if not subject_area:
        raise ValueError(f"Schema file {schema_path!r} missing 'subject_area'")
    cols = list(schema.get("columns", {}).keys())
    return {subject_area: cols}

def replace_all_in_source(data, schema_lookup):
    for subject_area, semantic_def in data.items():
        sources = semantic_def.get("source")

        # ✅ Ensure 'source' is a dictionary
        if not isinstance(sources, dict):
            print(f"❌ Invalid source format for subject area '{subject_area}', must be a dictionary.")
            continue

        for table_name, source in sources.items():
            if not isinstance(source, dict):
                print(f"⚠️ Skipping table '{table_name}' because source is not a dict.")
                continue

            columns = source.get("columns")
            # ✅ Check for <all> before replacing
            if isinstance(columns, str) and columns.strip() == "<all>":
                schema_subject = subject_area.lower()
                if schema_subject in schema_lookup:
                    actual_columns = schema_lookup[schema_subject]["columns"]
                    if isinstance(actual_columns, list):
                        data[subject_area]["source"][table_name]["columns"] = actual_columns
                        print(f"🔁 Replaced <all> for '{table_name}' with actual columns")
                        print(f"📜 Updated Columns for '{table_name}': {actual_columns}")
                else:
                    print(f"⚠️ Schema reference '{schema_subject}' not found in lookup")

# Base class for attributes and metrics
class AttributeMetricBase(BaseModel):
    name: str
    synonym: Optional[List[str]] = []
    desc: Optional[str]
    calculation: str
    consideration: Optional[str] = None
    function: Optional[Union[List[str], str]] = []
    fetch: Optional[bool] = False
    is_primary: Optional[bool] = False
    is_foreign: Optional[bool] = False

    model_config = {
        "extra": "forbid"
    }

    @field_validator("synonym")
    def synonym_must_be_list(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("synonym must be a list")
        return v

    @field_validator("function")
    def validate_function_is_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            if not all(isinstance(item, str) for item in v):
                raise ValueError("Each item in function must be a string")
            return v
        raise ValueError("function must be a string or a list of strings")
    
    @field_validator("calculation")
    def calculation_must_be_non_empty(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("calculation must be a non-empty string")
        return v

    @model_validator(mode="after")
    def check_conflicting_flags(cls, self):
        if self.is_primary and self.is_foreign:
            raise ValueError("Attribute cannot be both primary and foreign key")
        return self


# Main semantics block
class SemanticsBlock(BaseModel):
    folder: str
    type: str
    source: Dict[str, Dict[str, List[Union[str, int]]]]
    attributes: Dict[str, AttributeMetricBase]
    metrics: Dict[str, AttributeMetricBase]

    @field_validator("folder", "type")
    def must_be_string(cls, v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        return v

    @field_validator("source")
    def validate_source_structure(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Source must be a dictionary")
        for table, data in v.items():
            if not isinstance(data, dict) or "columns" not in data:
                raise ValueError("Each table in source must include a 'columns' dictionary")
            if not isinstance(data["columns"], list):
                raise ValueError("source.columns must be a list")
            for col in data["columns"]:
                if not isinstance(col, str):
                    raise ValueError("All source column names must be strings")
        return v

    @model_validator(mode="after")
    def validate_all(cls, self):
        folder = self.folder
        type_ = self.type
        source = self.source
        attributes = self.attributes if hasattr(self, 'attributes') else {}
        metrics = self.metrics if hasattr(self, 'metrics') else {}

        # ✅ Check for required keys
        required_keys = {"folder", "type", "source", "attributes", "metrics"}
        present_keys = set(self.__dict__.keys())
        missing_keys = required_keys - present_keys
        if missing_keys:
            raise ValueError(f"Missing required key(s): {missing_keys}")

        if not source:
            raise ValueError("source is required")

        # Collect defined columns from the source
        defined_columns = set()
        for table, config in source.items():
            columns_data = config.get("columns", {})
            if isinstance(columns_data, dict):
                defined_columns.update(columns_data.keys())
            elif isinstance(columns_data, list):
                defined_columns.update(columns_data)
            else:
                raise ValueError("Invalid columns format in source block")
        print("Defined Columns: ", defined_columns)

        # ✅ Validate attribute names and check for duplicates
        seen_attr_names = set()  # Track attribute names
        seen_names = set()  # Track names across attributes and metrics
        primary_count = 0
        for name, attr in attributes.items():
            if name in seen_attr_names:
                raise ValueError(f"Duplicate attribute name found in attributes block: {name}")
            seen_attr_names.add(name)

            if not is_valid_column_name(name):
                raise ValueError(f"Invalid attribute name: {name}")
            if name in RESERVED_NAMES:
                raise ValueError(f"Reserved keyword used as attribute name: {name}")

            # Extract columns referenced in the calculation field
            referenced_cols = re.findall(r"\[(.*?)\]", attr.calculation)
            for col in referenced_cols:
                if col not in defined_columns and col not in column_keys:
                    raise ValueError(f"Attribute '{name}' references unknown column: {col}")
                else:
                    print(f"Attribute '{name}' successfully references column: {col}")

        # ✅ Validate metric names and check for duplicates
        seen_metric_names = set()  # Track metric names
        for name, metric in metrics.items():
            if name in seen_metric_names:
                raise ValueError(f"Duplicate metric name found in metrics block: {name}")
            seen_metric_names.add(name)

            if not is_valid_column_name(name):
                raise ValueError(f"Invalid metric name: {name}")
            if name in RESERVED_NAMES:
                raise ValueError(f"Reserved keyword used as metric name: {name}")

            referenced_cols = re.findall(r"\[(.*?)\]", metric.calculation)
            for col in referenced_cols:
                if col in attributes:
                    raise ValueError(f"Metric '{name}' improperly references an attribute: {col}")
                if col not in defined_columns and col not in metrics and col not in column_keys:
                    raise ValueError(f"Metric '{name}' references unknown column or metric: {col}")
                else:
                    print(f"Metric '{name}' successfully references column: {col}")

        # ✅ Check for overlap between attributes and metrics (duplicate names)
        overlap = seen_attr_names & seen_metric_names
        if overlap:
            raise ValueError(f"Overlap between attributes and metrics: {overlap}")

        if primary_count > 1:
            raise ValueError("Only one primary key attribute is allowed")

        return self

# Root model for semantics
class SemanticsModel(RootModel):
    root: Dict[str, SemanticsBlock]

    def get_subject_areas(self):
        return list(self.root.keys())

# Custom error categorization
def get_custom_error_type(error):
    loc = error['loc']
    msg = error['msg'].lower()
    type_ = error['type'].lower()

    if "missing" in msg or "field required" in msg:
        return "MissingKeyError"
    elif "value is not a valid list" in msg or type_ == "list_type":
        return "InvalidFormatError"
    elif "value is not a valid string" in msg or type_ == "string_type":
        return "InvalidFormatError"
    elif "value is not a valid dict" in msg or "input should be a valid dictionary" in msg or type_ == "dict_type":
        return "InvalidFormatError"
    elif "all source column names must be strings" in msg:
        return "InvalidFormatError"
    elif "unexpected" in msg or "extra fields not permitted" in msg:
        return "InvalidFieldError"
    elif "value is not none and empty" in msg or "empty" in msg:
        return "EmptyValueError"
    elif "value error" in type_:
        return "ValueError"
    elif "invalid reference" in msg or "not defined in schema" in msg or "does not exist" in msg or "references unknown column" in msg:
        return "InvalidReferenceError"
    elif "redundant definition" in msg or "defined in both attributes and metrics" in msg:
        return "RedundantDefinitionError"
    elif "conflicting values" in msg or "duplicate definition" in msg:
        return "ConflictError"
    elif "reserved keyword" in msg or "invalid field name" in msg:
        return "InvalidFieldNameError"
    elif "unsupported function" in msg or "function not supported" in msg:
        return "UnsupportedFunctionError"
    elif "undefined metric" in msg or "not defined yet" in msg:
        return "UndefinedReferenceError"
    elif "metric references attribute" in msg or "invalid metric reference" in msg or "improperly references an attribute" in msg:
        return "InvalidMetricReferenceError"
    elif "extra fields not permitted" in msg or type_ == "extra_forbidden":
        return "InvalidFieldError"
    elif "overlap between attributes and metrics" in msg:
        return "ConflictError"
    else:
        return "ValidationError"


# Main execution for testing
if __name__ == "__main__":
    import sys

    schema_path = "assets/schema/game.yml"

    semantics_validator = SemanticsModel
    all_semantic_files = sorted(Path("test/semantics").glob("*.yaml"), key=lambda f: int("".join(filter(str.isdigit, f.name))))
    schema_lookup = {}

    try:
        # print("📦 Fetching schema...")
        schema_cols = load_schema(schema_path)
        schema_lookup = {
            subject_area.lower(): {
                "columns": columns
            } for subject_area, columns in schema_cols.items()
        }
        column_keys = list(schema_lookup.values())[0]["columns"]
        # print('🧩 Column Keys:', column_keys)
    except Exception as e:
        print(f"⚠️ Error loading schema: {e}")
        sys.exit(1)

    for semantic_file in all_semantic_files:
        try:
            print(f"\n📄 Processing file: {semantic_file.name}")
            with open(semantic_file, 'r') as f:
                file_content = f.read()
                if not file_content.strip():
                    print(f"❌ EmptyFileError: {semantic_file.name} is empty or only contains whitespace")
                    continue
                try:
                    data = yaml.safe_load(file_content)
                    # print(f"✅ Loaded {semantic_file.name}")
                except yaml.YAMLError as e:
                    # print(f"❌ YAML Load Error in {semantic_file.name}: {e}")
                    print(f"🔴 InvalidFormatError: {semantic_file.name} - {e}")
                    continue

            try:
                # print(f"🔄 Replacing <all> columns in {semantic_file.name}")
                replace_all_in_source(data, schema_lookup)
            except Exception as e:
                print(f"⚠️ Error processing <all>: {e}")
                continue

            try:
                print(f"🧪 Validating {semantic_file.name}")
                validated = semantics_validator.model_validate(data)
                print(f"✅ Passed: {semantic_file.name}")
            except ValidationError as e:
                print(f"❌ Validation Failed: {semantic_file.name}")
                for err in e.errors():
                    custom_error = get_custom_error_type(err)
                    print(f"🔴 {custom_error}: {'.'.join(str(i) for i in err['loc'])} - {err['msg']}")

        except Exception as e:
            print(f"⚠️ Error processing file {semantic_file.name}: {e}")
