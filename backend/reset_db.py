import asyncio
from app.database import engine, Base
from app.models import *

async def reset():
    async with engine.begin() as conn:
        print('Suppression des tables existantes...')
        await conn.run_sync(Base.metadata.drop_all)
        print('Recréation des tables vierges...')
        await conn.run_sync(Base.metadata.create_all)
    print('Base de données réinitialisée avec succès !')

if __name__ == '__main__':
    asyncio.run(reset())