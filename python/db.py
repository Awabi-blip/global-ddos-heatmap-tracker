import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row  
import psycopg # The standard sync import
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

pool = AsyncConnectionPool(
conninfo=DATABASE_URL,
kwargs={"row_factory": dict_row, "autocommit": True},
min_size = 1,
max_size = 20,
open = False
)

async def app_sql(sql : str, parameters : tuple[Any] = ()) -> Optional[list[dict[str,any]]]:
    try:
        async with pool.connection() as connection:
           async with connection.cursor() as cursor:
                await cursor.execute(sql,parameters)
                
                if cursor.description:
                    return await cursor.fetchall()
                                
                return None
    
    except Exception as e:
        print(f"Database Error: {e}")
        return None
            

def script_sql(sql: str, parameters: tuple[Any, ...] = ()) -> Optional[list[dict[str, Any]]]:
    try:
        # Connect using the standard sync connection
        with psycopg.connect(
            os.getenv("DATABASE_URL"),
            row_factory=dict_row
        ) as connection:
            # Transactions are handled automatically by the 'with' block in psycopg3
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                
                # Check if the query returns rows (like SELECT) or not (like INSERT/UPDATE)
                if cursor.description:
                    return cursor.fetchall()
                
                return None

    except Exception as e:
        print(f"Database Error: {e}")
        return None

async def executeMany_sql(sql: str, data: list[dict[str,any]]) -> Optional[list[dict[str,str]]]:
    try:
        async with await psycopg.AsyncConnection.connect(
            os.getenv("DATABASE_URL"),
            row_factory=dict_row,
        ) as connection:
            
            async with connection.transaction():
                async with connection.cursor() as cursor:
                    await cursor.executemany(sql, data)
                    
                    if cursor.description:
                        result = await cursor.fetchall()
                    else:
                        result = None  
                    return result

    
    except Exception as e:
        print(f"Database Error: {e}")