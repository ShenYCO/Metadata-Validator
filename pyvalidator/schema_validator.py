import yaml
from typing import List, Dict
from format_validator import SchemaWrapper, GeneratedSchema, TableInfo, Column
from simple_ddl_parser import DDLParser
from pprint import pprint



def parse_ddl_to_metadata(ddl:str):
    return DDLParser(ddl).run(output_mode="hql")



class SchemaValidator():
    
    TYPE_EQUIVALENTS = {
                "NUMBER": {"DECIMAL", "FLOAT", "NUMBER", "DOUBLE", "NUMERIC"},
                "INT": {"INT", "INTEGER", "BIGINT", "SMALLINT"},
                "VARCHAR": {"VARCHAR", "TEXT", "STRING", "CHAR"},
                "DATE": {"DATE", "DATETIME", "TIMESTAMP"}
            }
    
    
    def __init__(self, ddls = None):
        self.ddl = parse_ddl_to_metadata(ddls)
        
    
    def print_ddl(self):
        pprint(self.ddl)
        
        
    def types_are_equivalent(self,ddl_type: str, schema_type: str) -> bool:
        ddl_type = ddl_type.upper()
        schema_type = schema_type.upper()
        for equivalents in self.TYPE_EQUIVALENTS.values():
            if ddl_type in equivalents and schema_type in equivalents:
                return True
        return ddl_type == schema_type  # fallback: exact match
    
    
    
           
    def validate_schema(self, generated_schema: Dict):
        
        
        schema_key = list(generated_schema.keys())[0]
        
        schema = generated_schema[schema_key]
        # print(schema)
        
        
        schema = GeneratedSchema(**schema)
        schema_table_name = schema.table_info[0].table

        
        if schema_table_name != self.ddl[0]["table_name"]:
            raise ValueError(f"{schema.table_info[0].table} table name not in DDL")
        
        schema_columns = {col.column: col for col in schema.columns.values()} 

        ddl_primary_keys = self.ddl[0]["primary_key"]  # checking primary keys too
        # Step 3: Validate DDL columns against schema
        for ddl_col in self.ddl[0]['columns']:
            ddl_col_name = ddl_col['name']
            ddl_col_type = ddl_col['type'].upper()

            if ddl_col_name not in list(schema_columns.keys()):
                raise ValueError(f"DDL column '{ddl_col_name}' not found in schema.")

            schema_col_type = schema_columns[ddl_col_name].type.upper()
            if not self.types_are_equivalent(ddl_col_type, schema_col_type):
                raise ValueError(f"Type mismatch for column '{ddl_col_name}': DDL type '{ddl_col_type}', Schema type '{schema_col_type}'.")
            
            
            if ddl_col_name in ddl_primary_keys:
                if not schema.columns[ddl_col_name].primary_key:
                    raise ValueError(f"{ddl_col_name} not stated as primary key in Schema")
                
            elif schema.columns[ddl_col_name].primary_key:
                raise ValueError(f"{ddl_col_name} stated as primary key in Schema which isn't a primary key")
            
            if schema_columns[ddl_col_name].fetch:
                if schema_columns[ddl_col_name].type.upper() == "NUMBER":
                    raise ValueError(f"Invalid Fetch value for {schema_columns[ddl_col_name]}. Column type is number ")
            

        print("Schema successfully validated against DDL.")
                
                
        




