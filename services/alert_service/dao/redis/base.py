from redis.client import Redis

from dao.redis.key_schema import KeySchema


class RedisDaoBase:
    """Shared functionality for Redis DAO classes."""

    def __init__(self, redis_client: Redis, key_schema: KeySchema = None, **kwargs) -> None:
        if not isinstance(redis_client, Redis):
            raise TypeError("redis_client must be an instance of redis.Redis")

        self.redis_client = redis_client
        if key_schema is None:
            key_schema = KeySchema()
        self.key_schema = key_schema
