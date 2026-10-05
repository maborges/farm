import asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
# Connect to DB. Assuming postgres... let's just query via psql or similar.
