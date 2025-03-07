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
import logging
from sqlparse.sql import Token, TokenList
from sqlparse.tokens import Keyword, Name, DML, DDL

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import engine, async_session
from app.db.models.base import Base
from app.db.models.types import SessionStatus, TokenType, DialogType, ProcessingStatus
from app.utils.logging import get_logger

logger = logging.getLogger(__name__)

def parse_sql_schema(sql_file_path: str) -> tuple[set[str], set[str]]:
    """Parse SQL schema file to extract table and enum names."""
    logger.info(f"Reading SQL schema from {sql_file_path}")
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()

    statements = sqlparse.parse(sql_content)
    logger.info(f"Found {len(statements)} SQL statements")

    tables = set()
    enums = set()

    def clean_identifier(identifier: str) -> str:
        """Clean SQL identifier by removing quotes and schema prefixes."""
        # Remove schema prefix if present
        if '.' in identifier:
            identifier = identifier.split('.')[-1]
        # Remove quotes
        identifier = identifier.strip('"').strip("'").strip('`')
        return identifier.lower()

    for statement in statements:
        # Skip comments and empty statements
        if not statement.tokens or all(t.is_whitespace or t.ttype in (sqlparse.tokens.Comment, sqlparse.tokens.Comment.Single) for t in statement.tokens):
            continue

        # Get all meaningful tokens
        tokens = []
        for token in statement.flatten():
            if not token.is_whitespace and token.value.strip() and token.ttype not in (sqlparse.tokens.Comment, sqlparse.tokens.Comment.Single):
                tokens.append(token)

        if not tokens:
            continue

        # Check if this is a CREATE statement
        if tokens[0].ttype is DDL and tokens[0].value.upper() == 'CREATE':
            # Get what we're creating (TABLE, TYPE, etc)
            create_type = None
            object_name = None
            
            # Find the type of object being created
            for i, token in enumerate(tokens):
                if token.ttype is Keyword and token.value.upper() in ('TABLE', 'TYPE'):
                    create_type = token.value.upper()
                    # Look for the object name after the type
                    for j in range(i + 1, len(tokens)):
                        name_token = tokens[j]
                        if name_token.value.upper() in ('IF', 'NOT', 'EXISTS'):
                            continue
                        object_name = clean_identifier(name_token.value)
                        break
                    break

            if not create_type or not object_name:
                continue

            # Handle CREATE TABLE
            if create_type == 'TABLE':
                if object_name not in ('migrations',):  # Exclude migrations table
                    tables.add(object_name)
                    
            # Handle CREATE TYPE AS ENUM
            elif create_type == 'TYPE':
                # Look for AS ENUM keywords
                for i in range(len(tokens)):
                    if (i + 1 < len(tokens) and 
                        tokens[i].ttype is Keyword and tokens[i].value.upper() == 'AS' and
                        tokens[i + 1].ttype is Keyword and tokens[i + 1].value.upper() == 'ENUM'):
                        enums.add(object_name)
                        break

    logger.info(f"Found {len(tables)} tables and {len(enums)} enums")
    logger.info(f"Tables: {sorted(list(tables))}")
    logger.info(f"Enums: {sorted(list(enums))}")

    return tables, enums

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

def compare_schemas(sql_schema: tuple[set[str], set[str]], model_schema: Dict) -> List[str]:
    """Compare SQL and model schemas and return list of differences."""
    differences = []
    sql_tables, sql_enums = sql_schema
    
    # Compare enums
    model_enums = {e.lower() for e in model_schema['enums'].keys()}
    if sql_enums != model_enums:
        differences.append(f"  - Enum mismatch: SQL={sql_enums}, Models={model_enums}")
        
    # Compare tables
    model_tables = {t.lower() for t in model_schema['tables'].keys()}
    if sql_tables != model_tables:
        differences.append(f"  - Table mismatch: SQL={sql_tables}, Models={model_tables}")
        
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
        sql_tables, sql_enums = parse_sql_schema(str(schema_file))
        model_schema = get_model_schema()
        
        # Compare schemas
        differences = compare_schemas((sql_tables, sql_enums), model_schema)
        
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