import re
from pydantic import BaseModel, field_validator, model_validator, ValidationError
from typing import List, Dict, Optional, Generic, TypeVar, Type
import sys
import os
from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

# Add project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logger.log import logger


# ========== MODELS ==========
class TableInfo(BaseModel):
    table: str
    joins: List[str]

    @field_validator('joins')
    @classmethod
    def _validate_joins_format(cls, joins):
        if not isinstance(joins, list):
            raise TypeError("InvalidFormatError: 'joins' must be a list.")

        if not joins:
            return joins

        for condition in joins:
            pattern = r'^[\w]+\.[\w]+\s*=\s*[\w]+\.[\w]+$'
            if not isinstance(condition, str) or not re.match(pattern, condition):
                raise ValueError(
                    f'Invalid join condition format: "{condition}". Expected format: "table.column = table.column"'
                )
        return joins


    @field_validator('table')
    @classmethod
    def _empty_table(cls, table_name):
        if table_name.strip() == "":
            raise ValueError("Empty table name in table_info")
        return table_name

    @model_validator(mode="after")
    def _check_required_keys(self):
        # Validate that both table and joins exist
        if self.table is None:
            raise ValueError("MissingKeyError: 'table' is required in table_info.")
        if self.joins is None:
            raise ValueError("MissingKeyError: 'joins' is required in table_info.")
        return self
    
class Column(BaseModel):
    name: str
    type: str
    column: str
    desc: str
    primary_key: Optional[bool] = None
    foreign_key: Optional[bool] = None
    table: Optional[str] = None
    fetch: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def check_empty_name(cls, v):
        if not v.strip():  # If the name is an empty string or only whitespace
            raise ValueError("EmptyValueError: 'name' must not be empty.")
        return v

class GeneratedSchema(BaseModel):
    subject_area: str
    table_info: List[TableInfo]
    columns: Dict[str, Column]

    @field_validator('table_info')
    @classmethod
    def check_table_info_not_empty(cls, v):
        if not v:
            raise ValueError("EmptyValueError: 'table_info' must not be empty.")
        return v

    @field_validator('columns')
    @classmethod
    def check_columns_not_empty(cls, v):
        if not v:
            raise ValueError("EmptyValueError: 'columns' must not be empty.")
        return v

    @model_validator(mode="after")
    def _check_unique_column_id(self):
        column_ids = list(self.columns.keys())
        if len(column_ids) != len(set(column_ids)):
            raise ValueError("InvalidKeyError: Column IDs are not unique")
        return self

    @model_validator(mode="after")
    def _check_column_name_format(self):
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        for column_id in self.columns:
            if not re.match(pattern, column_id):
                raise ValueError(f"InvalidFormatError: Column ID '{column_id}' does not match the required pattern.")
        return self

    @model_validator(mode="after")
    def _validate_table_reference(self):
        defined_tables = {table.table for table in self.table_info}
        for column_id, column in self.columns.items():
            if column.table:
                references = column.table if isinstance(column.table, list) else [column.table]
                for ref in references:
                    if ref not in defined_tables:
                        raise ValueError(f"MissingKeyError: Table reference '{ref}' in column '{column_id}' not found.")
        return self


GeneratedSchemaType = TypeVar('GeneratedSchemaType', bound=GeneratedSchema)


class SchemaWrapper(BaseModel, Generic[GeneratedSchemaType]):
    root: Dict[str, GeneratedSchemaType]


class SourceColumns(BaseModel):
    columns: List[str]


class Attributes(BaseModel):
    name: str
    synonym: Optional[List[str]] = None
    description: str
    include: Optional[List[str]] = None
    output_consideration: Optional[str] = None
    relevant_attributes: Optional[List[str]] = None


class Metrics(BaseModel):
    name: str
    synonym: Optional[List[str]] = None
    description: Optional[str] = None
    calculation: Optional[str] = None
    granularity: Optional[List[str]] = None
    include: Optional[List[str]] = None
    function: Optional[str] = None


class GeneratedSemantics(BaseModel):
    folder: str
    type: str
    source: Optional[Dict[str, SourceColumns]] = None
    attributes: Dict[str, Attributes]
    metrics: Dict[str, Metrics]


GeneratedSemanticsType = TypeVar("GeneratedSemanticsType", bound=GeneratedSemantics)


class SemanticWrapper(BaseModel, Generic[GeneratedSemanticsType]):
    root: Dict[str, GeneratedSemanticsType]


# ========== VALIDATOR ENTRY POINT ==========

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_validator.py <path_to_yaml_file>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    yaml = YAML()
    yaml.allow_duplicate_keys = False  # catch duplicate keys like test case 15

    try:
        with open(yaml_path, 'r') as f:
            data = yaml.load(f)
            if not data:
                raise ValueError("The schema file is empty.")
    except DuplicateKeyError as dke:
        logger.error(f"InvalidKeyError: Duplicate key found. {dke}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"EmptyFileError: {e}")
        sys.exit(1)

    try:
        SchemaWrapper[GeneratedSchema](root=data)
        logger.info(f"Format validation passed for file: {yaml_path}")
    except ValidationError as ve:
        # logger.error(f"Format validation failed for file: {yaml_path}")
        for err in ve.errors():
            loc = ".".join(str(i) for i in err['loc'])
            msg = err['msg']
            type_ = err['type']

            if "missing" in type_:
                logger.error(f"   MissingKeyError: '{loc}' is required.")
            elif "list_type" in type_ or "dict_type" in type_:
                logger.error(f"   InvalidFormatError: '{loc}' has invalid format. {msg}")
            elif "bool_parsing" in type_:
                logger.error(f"   InvalidFormatError: Expected a boolean in '{loc}'. {msg}")
            elif "string_type" in type_:
                logger.error(f"   EmptyValueError: '{loc}' must be a non-empty string.")
            elif "model_type" in type_:
                logger.error(f"   InvalidFormatError: '{loc}' must be a dictionary, not a list.")
            elif "EmptyValueError" in msg:
                # Change the error to match the desired format
                logger.error(f"   EmptyValueError at '{loc}'")
            else:
                logger.error(f"   ValidationError at '{loc}': {msg}")

        sys.exit(1)
