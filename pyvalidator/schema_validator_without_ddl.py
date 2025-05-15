import yaml
from typing import Dict
from format_validator import GeneratedSchema
from pprint import pprint
from simple_ddl_parser import DDLParser
import sys
import os

# Add project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logger.log import logger

def parse_ddl_to_metadata(ddl: str):
    return DDLParser(ddl).run(output_mode="hql")


class SchemaValidator:
    TYPE_EQUIVALENTS = {
        "NUMBER": {"DECIMAL", "FLOAT", "NUMBER", "DOUBLE", "NUMERIC"},
        "INT": {"INT", "INTEGER", "BIGINT", "SMALLINT"},
        "VARCHAR": {"VARCHAR", "TEXT", "STRING", "CHAR"},
        "DATE": {"DATE", "DATETIME", "TIMESTAMP"},
    }

    def __init__(self, ddls=None):
        self.ddl = parse_ddl_to_metadata(ddls) if ddls else None

    def print_ddl(self):
        pprint(self.ddl)

    def types_are_equivalent(self, ddl_type: str, schema_type: str) -> bool:
        ddl_type = ddl_type.upper()
        schema_type = schema_type.upper()
        for equivalents in self.TYPE_EQUIVALENTS.values():
            if ddl_type in equivalents and schema_type in equivalents:
                return True
        return ddl_type == schema_type  # fallback: exact match

    def validate_schema(self, generated_schema: Dict):
        # if not generated_schema:
        #     raise ValueError("EmptyFileError: The schema file is empty.")

        schema_key = list(generated_schema.keys())[0]
        schema_data = generated_schema[schema_key]

        try:
            schema = GeneratedSchema(**schema_data)
            logger.info(f"✅ Format and structure for '{schema_key}' validated.")
        except Exception as e:
            logger.error(f"❌ Failed to validate format for '{schema_key}': {e}")
            raise

        if not self.ddl:
            logger.info("ℹ️ No DDL provided — skipping DDL-based validation.")
            return

        schema_table_name = schema.table_info[0].table
        ddl_table_name = self.ddl[0]["table_name"]

        if schema_table_name != ddl_table_name:
            error_msg = f"'{schema_table_name}' not found in DDL definition (expected '{ddl_table_name}')."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        schema_columns = {col.column: col for col in schema.columns.values()}
        ddl_primary_keys = self.ddl[0]["primary_key"]

        for ddl_col in self.ddl[0]["columns"]:
            ddl_col_name = ddl_col["name"]
            ddl_col_type = ddl_col["type"].upper()

            if ddl_col_name not in schema_columns:
                error_msg = f"DDL column '{ddl_col_name}' not found in schema."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            schema_col_type = schema_columns[ddl_col_name].type.upper()
            if not self.types_are_equivalent(ddl_col_type, schema_col_type):
                error_msg = (
                    f"Type mismatch for '{ddl_col_name}': DDL='{ddl_col_type}', Schema='{schema_col_type}'"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            if ddl_col_name in ddl_primary_keys:
                if not schema.columns[ddl_col_name].primary_key:
                    error_msg = f"{ddl_col_name} not marked as primary key in schema."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            elif schema.columns[ddl_col_name].primary_key:
                error_msg = f"{ddl_col_name} marked as primary key in schema but not in DDL."
                logger.error(error_msg)
                raise ValueError(error_msg)

            if schema_columns[ddl_col_name].fetch:
                if schema_columns[ddl_col_name].type.upper() == "NUMBER":
                    error_msg = f"Invalid fetch value for numeric column '{ddl_col_name}'"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        logger.info("✅ Schema successfully validated against DDL.")

