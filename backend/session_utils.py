import aioredis
from config import settings

# Используем aioredis для асинхронной работы с Redis
redis_client = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True)

async def store_session(user_id: int, session_data: dict):
    async with redis_client.pipeline() as pipe:
        await pipe.hmset(f"user:{user_id}:session", session_data)
        await pipe.execute()

async def get_session(user_id: int):
    return await redis_client.hgetall(f"user:{user_id}:session")