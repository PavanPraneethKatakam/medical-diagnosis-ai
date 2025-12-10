"""
Database Utilities - Transaction safety and connection management

Provides context managers and utilities for safe database operations.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator


@contextmanager
def get_db_connection(db_path: str = "database/medical_knowledge.db") -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    
    Automatically closes connection on exit.
    
    Args:
        db_path: Path to SQLite database
        
    Yields:
        Database connection
        
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patients")
    """
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager for database transactions.
    
    Automatically commits on success, rolls back on exception.
    
    Args:
        conn: Database connection
        
    Yields:
        Database cursor
        
    Example:
        with get_db_connection() as conn:
            with transaction(conn) as cursor:
                cursor.execute("INSERT INTO ...", (val1, val2))
                cursor.execute("UPDATE ...", (val3,))
            # Auto-commit here
    """
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


def execute_query(
    db_path: str,
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    fetch_all: bool = True
):
    """
    Execute a SELECT query with automatic connection management.
    
    Args:
        db_path: Path to database
        query: SQL query
        params: Query parameters (use ? placeholders)
        fetch_one: Return single row
        fetch_all: Return all rows
        
    Returns:
        Query results
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return None


def execute_write(
    db_path: str,
    query: str,
    params: tuple = ()
):
    """
    Execute an INSERT/UPDATE/DELETE query with transaction safety.
    
    Args:
        db_path: Path to database
        query: SQL query
        params: Query parameters (use ? placeholders)
        
    Returns:
        Last row ID for INSERT, row count for UPDATE/DELETE
    """
    with get_db_connection(db_path) as conn:
        with transaction(conn) as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid if "INSERT" in query.upper() else cursor.rowcount


def execute_many(
    db_path: str,
    query: str,
    params_list: list
):
    """
    Execute multiple statements in a single transaction.
    
    Args:
        db_path: Path to database
        query: SQL query
        params_list: List of parameter tuples
        
    Returns:
        Number of rows affected
    """
    with get_db_connection(db_path) as conn:
        with transaction(conn) as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
