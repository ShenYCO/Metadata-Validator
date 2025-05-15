import re
from pydantic import BaseModel, field_validator, model_validator
from typing import List, Dict, Optional, Generic, TypeVar, Type            
import sys
import yaml    

class TableInfo(BaseModel):
    table: str
    joins: List[str]
    
    
    @field_validator('joins')
    @classmethod
    def _validate_joins_format(cls, joins):
        if not joins:
            return joins
        
        for condition in joins:
            pattern = r'^[\w]+\.[\w]+\s*=\s*[\w]+\.[\w]+$'
            if not isinstance(condition,str) or not re.match(pattern,condition):
                raise ValueError(
                    f'Invalid join condition format: "{condition}". Expected format: "table.column = table.column"'
                )
        return joins
    
    @field_validator('table')
    @classmethod
    def _empty_table(cls,table_name):
        if table_name.strip() == "":
            raise ValueError("Empty table name in table_info")
        return table_name
    
    
class Column(BaseModel):
    name: str
    type: str
    column: str
    desc: str
    primary_key: Optional[bool] = None
    foreign_key: Optional[bool] = None
    table : Optional[str] = None
    fetch: Optional[bool] = None
    

class GeneratedSchema(BaseModel):
    subject_area: str
    table_info: List[TableInfo]
    columns: Dict[str, Column]
    
    
    # tables_in_schema = {table.table for table in table_info}
    
    
    @model_validator(mode="after")
    def _check_unique_column_id(self):
        columns = list(self.columns.keys())
        print(columns)
        # columns = values.get("columns",{})
        column_ids = set()
        for column_id in columns:
            if column_id not in column_ids:
                column_ids.add(column_id)
            else:
                raise ValueError("Columns ids not unique")
        return self   
    
    @model_validator( mode="after")
    def _check_column_name_format(self):
        columns = self.columns
        # columns = values.get("columns",{})
        pattern = r'[a-zA-Z_][a-zA-Z0-9_]*$'
        for column_id, column in columns.items():
            if not re.match(pattern, column_id):
                raise ValueError(f"Column name: {column_id} not matching with the column name format")  
        return self
        
    @model_validator(mode="after")
    def _validate_table_reference(self):
        tables_set = set()
        tables = self.table_info
        for table in tables:
            tables_set.add(table.table)
        
        columns = self.columns
        for column_id, column in columns.items():
            if column.table != None:
                if type(column.table) == str:
                    reference = column.table
                    if reference not in tables_set:
                        raise ValueError(f"{column['table']} reference missing")
                elif type(column.table) == list:
                    for reference in column['table']:
                        if reference not in tables_set:
                            raise ValueError(f"{column['table']} reference missing")
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
    



# SourceType = TypeVar("SourceType", bound=Source)
class GeneratedSemantics(BaseModel):
    folder: str
    type: str
    source: Optional[Dict[str,SourceColumns]] = None
    attributes: Dict[str, Attributes]
    metrics: Dict[str, Metrics]
    
    
GeneratedSemanticsType = TypeVar("GeneratedScemanticsType", bound= GeneratedSemantics)
class SemanticWrapper(BaseModel, Generic[GeneratedSemanticsType]):
    root: Dict[str, GeneratedSemanticsType]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python format_validator.py <path_to_yaml_file>")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    try:
        SchemaWrapper[GeneratedSchema](root=data)
        print("Format validation passed.")
    except Exception as e:
        print(f"Format validation failed: {e}")
        sys.exit(1)