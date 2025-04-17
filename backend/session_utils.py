# import aioredis
# from config import settings

# redis_client = aioredis.from_url(
#     f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}",
#     decode_responses=True
# )

# async def store_session(user_id: int, session_data: dict):
#     async with redis_client.pipeline() as pipe:
#         await pipe.hset(f"user:{user_id}:session", mapping=session_data)
#         await pipe.execute()

# async def get_session(user_id: int):
#     return await redis_client.hgetall(f"user:{user_id}:session")