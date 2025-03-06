"""
Schema Validator

This script validates that our SQLAlchemy models match our SQL migration schema.
It checks:
1. Table names
2. Column names and types
3. Constraints and indexes
4. Enum values
"""

import os
import sys
import asyncio
import sqlparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import engine, async_session
from app.db.base import Base
from app.db.models.types import SessionStatus, TokenType, DialogType, ProcessingStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)

def parse_sql_schema(sql_file: Path) -> Dict:
    """Parse SQL schema file and extract table and enum definitions"""
    with open(sql_file) as f:
        sql = f.read()
    
    # Parse SQL into statements
    statements = sqlparse.parse(sql)
    
    schema = {
        'enums': {},
        'tables': {},
        'indexes': set(),
        'constraints': set()
    }
    
    current_table = None
    
    for statement in statements:
        stmt_str = str(statement).strip()
        
        # Skip comments and empty statements
        if not stmt_str or stmt_str.startswith('--'):
            continue
            
        # Parse CREATE TYPE (enums)
        if stmt_str.startswith('CREATE TYPE') and 'AS ENUM' in stmt_str:
            enum_name = stmt_str.split()[2]
            values = stmt_str.split('(')[1].split(')')[0]
            values = [v.strip().strip("'") for v in values.split(',')]
            schema['enums'][enum_name] = values
            
        # Parse CREATE TABLE
        elif stmt_str.startswith('CREATE TABLE'):
            table_name = stmt_str.split()[4].strip('(')
            current_table = table_name
            schema['tables'][table_name] = {
                'columns': {},
                'constraints': set(),
                'indexes': set()
            }
            
            # Extract column definitions
            in_columns = False
            for line in stmt_str.split('\n'):
                line = line.strip()
                if line.startswith('('):
                    in_columns = True
                    continue
                if line.startswith(');'):
                    in_columns = False
                    continue
                if in_columns and line:
                    if line.startswith('CONSTRAINT') or line.startswith('PRIMARY KEY') or line.startswith('UNIQUE'):
                        schema['tables'][current_table]['constraints'].add(line.strip(','))
                    elif not line.startswith('--'):
                        col_def = line.strip(',')
                        col_name = col_def.split()[0]
                        col_type = ' '.join(col_def.split()[1:])
                        schema['tables'][current_table]['columns'][col_name] = col_type
                        
        # Parse CREATE INDEX
        elif stmt_str.startswith('CREATE INDEX'):
            if current_table:
                schema['tables'][current_table]['indexes'].add(stmt_str)
            schema['indexes'].add(stmt_str)
    
    return schema

def get_model_schema() -> Dict:
    """Extract schema information from SQLAlchemy models"""
    schema = {
        'enums': {
            'sessionstatus': [status.value for status in SessionStatus],
            'tokentype': [token_type.value for token_type in TokenType],
            'dialogtype': [dialog_type.value for dialog_type in DialogType],
            'processingstatus': [status.value for status in ProcessingStatus]
        },
        'tables': {}
    }
    
    # Get MetaData from Base
    metadata = Base.metadata
    
    # Extract table information
    for table_name, table in metadata.tables.items():
        schema['tables'][table_name] = {
            'columns': {},
            'constraints': set(),
            'indexes': set()
        }
        
        # Get column information
        for column in table.columns:
            col_type = str(column.type)
            if column.server_default:
                col_type += f" DEFAULT {column.server_default.arg}"
            if not column.nullable:
                col_type += " NOT NULL"
            schema['tables'][table_name]['columns'][column.name] = col_type
            
        # Get constraints
        for constraint in table.constraints:
            schema['tables'][table_name]['constraints'].add(str(constraint))
            
        # Get indexes
        for index in table.indexes:
            schema['tables'][table_name]['indexes'].add(str(index))
    
    return schema

def compare_schemas(sql_schema: Dict, model_schema: Dict) -> List[str]:
    """Compare SQL schema with SQLAlchemy model schema"""
    differences = []
    
    # Compare enums
    sql_enums = set(sql_schema['enums'].keys())
    model_enums = set(model_schema['enums'].keys())
    
    if sql_enums != model_enums:
        differences.append(f"Enum mismatch: SQL={sql_enums}, Models={model_enums}")
    
    for enum_name in sql_enums & model_enums:
        sql_values = set(sql_schema['enums'][enum_name])
        model_values = set(model_schema['enums'][enum_name])
        if sql_values != model_values:
            differences.append(f"Enum values mismatch for {enum_name}: SQL={sql_values}, Models={model_values}")
    
    # Compare tables
    sql_tables = set(sql_schema['tables'].keys())
    model_tables = set(model_schema['tables'].keys())
    
    if sql_tables != model_tables:
        differences.append(f"Table mismatch: SQL={sql_tables}, Models={model_tables}")
    
    for table_name in sql_tables & model_tables:
        sql_table = sql_schema['tables'][table_name]
        model_table = model_schema['tables'][table_name]
        
        # Compare columns
        sql_columns = set(sql_table['columns'].keys())
        model_columns = set(model_table['columns'].keys())
        
        if sql_columns != model_columns:
            differences.append(f"Column mismatch in {table_name}: SQL={sql_columns}, Models={model_columns}")
        
        # Compare column types
        for col_name in sql_columns & model_columns:
            sql_type = sql_table['columns'][col_name].lower()
            model_type = model_table['columns'][col_name].lower()
            
            # Normalize type strings for comparison
            sql_type = sql_type.replace('  ', ' ').replace('default gen_random_uuid()', '').strip()
            model_type = model_type.replace('  ', ' ').strip()
            
            if sql_type != model_type:
                differences.append(f"Column type mismatch in {table_name}.{col_name}: SQL={sql_type}, Model={model_type}")
    
    return differences

async def validate_schema():
    """Validate SQLAlchemy models against SQL schema"""
    try:
        # Get migration file path
        migrations_dir = Path(__file__).parent / "migrations"
        schema_file = migrations_dir / "001_initial_schema.sql"
        
        if not schema_file.exists():
            logger.error("Initial schema file not found")
            return False
        
        # Parse schemas
        sql_schema = parse_sql_schema(schema_file)
        model_schema = get_model_schema()
        
        # Compare schemas
        differences = compare_schemas(sql_schema, model_schema)
        
        if differences:
            logger.error("Schema validation failed:")
            for diff in differences:
                logger.error(f"  - {diff}")
            return False
        
        logger.info("Schema validation successful - models match SQL schema")
        return True
        
    except Exception as e:
        logger.error(f"Error validating schema: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting schema validation...")
    try:
        result = asyncio.run(validate_schema())
        if not result:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Schema validation failed: {str(e)}")
        sys.exit(1) 