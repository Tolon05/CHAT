import redis.asyncio as redis
from backend.config import settings

redis_client = redis.from_url(
    f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}",
    decode_responses=True
)

async def store_session(user_id: int, session_data: dict):
    async with redis_client.pipeline() as pipe:
        await pipe.hset(f"user:{user_id}:session", mapping=session_data)
        await pipe.execute()

async def get_session(user_id: int):
    return await redis_client.hgetall(f"user:{user_id}:session")

async def store_verification_code(email: str, code: str, expires_minutes: int = 5):
    key = f"verify:{email}"
    await redis_client.set(key, code, ex=expires_minutes * 60)  

async def verify_code(email: str, input_code: str) -> bool:
    key = f"verify:{email}"
    saved_code = await redis_client.get(key)
    return saved_code == input_code

async def delete_verification_code(email: str):
    key = f"verify:{email}"
    await redis_client.delete(key)