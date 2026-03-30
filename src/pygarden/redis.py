#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis connection and message handling.
"""

import json
from typing import Any, Dict, Optional
from redis import Redis
from dataclasses import asdict, is_dataclass
from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

def _default_serializer(obj: Any) -> Any:
    """Make common objects JSON-serializable (dataclasses -> dict, fallback -> str)."""
    if is_dataclass(obj):
        return asdict(obj)
    try:
        return obj.__dict__
    except Exception:
        return str(obj)

class Redis:
    """
    Provides Redis connection using environment variables for configuration.
    """
    DEFAULT_URL = ce("REDIS_URL", None)
    DEFAULT_HOST = ce("REDIS_HOST", "localhost")
    DEFAULT_PORT = ce("REDIS_PORT", 6379)
    
    DEFAULT_LOG_PATH = ce("REDIS_LOG_FILE", "")
    DEFAULT_LOG_MODE = ce("REDIS_LOG_MODE", "a")
    DEFAULT_LOG_ENCODING = ce("REDIS_LOG_ENCODING", "utf-8")

    def __init__(
        self,
        log_file_info: Optional[dict] = None,
        connection_info: Optional[dict] = None,
        **kwargs: Dict[str, Any],
    ):
        """Create a Redis object

        :param log_file_info: A dictionary containing log file info.
        :param connection_info: A dictionary containing connection info.
        """
        if connection_info is None:
            connection_info = {}
        self.url = connection_info.get("url", Redis.DEFAULT_URL)
        if self.url is None:
            self.url = f"redis://{connection_info.get('host', Redis.DEFAULT_HOST)}:{connection_info.get('port', Redis.DEFAULT_PORT)}"
        self.client = Redis.from_url(self.url, **kwargs)
        
        if log_file_info is None:
            log_file_info = {
                "path": Redis.DEFAULT_LOG_PATH,
                "mode": Redis.DEFAULT_LOG_MODE,
                "encoding": Redis.DEFAULT_LOG_ENCODING,
            }
        if log_file_info["path"] == "":
            self.logger = create_logger()
        else:
            self.logger = create_logger(log_file_info["path"], log_file_info["mode"], log_file_info["encoding"])

    @staticmethod
    def from_url(url: str, **kwargs) -> Redis:
        """Generate a Redis option from a connection URL.

        :param url: The Redis connection URL.
        :type url: str
        :return: A Redis instance connected to the specified URL.
        :rtype: Redis
        """
        return Redis(connection_info={"url": url}, **kwargs)

    # Including this as to make it a drop in replace for redis.Redis
    def setex(self, name: str, time: int, value: str) -> None:
        """Set a value in the redis store with an expiration time.

        :param name: The name of the key to set.
        :type name: str
        :param time: The expiration time in seconds.
        :type time: int
        :param value: The value to set.
        :type value: str
        """
        self.client.setex(name, time, value)
    
    # Including this as to make it a drop in replace for redis.Redis
    def set(self, name: str, value: str) -> None:
        """Set a value in the redis store.

        :param name: The name of the key to set.
        :type name: str
        :param value: The value to set.
        :type value: str
        """
        self.client.set(name, value)
    
    def publish(self, name: str, payload: Any, *, ttl_seconds: Optional[int] = None) -> None:
        """Publish to the redis store.

        :param name: The name of the key to publish to.
        :type name: str
        :param payload: The data to publish.
        :type payload: Any
        :param ttl_seconds: Time-to-live for the key in seconds, defaults to None
        :type ttl_seconds: Optional[int], optional
        """
        data = json.dumps(payload, default=_default_serializer)
        if ttl_seconds:
            self.setex(name, ttl_seconds, data)
        else:
            self.set(name, data)

    # Including this as to make it a drop in replace for redis.Redis
    def get(self, name: str) -> Optional[str]:
        """Get a raw value from the redis store.

        :param name: The name of the key to get.
        :type name: str
        :return: The raw value as a string, or None if the key does not exist or an error occurs.
        :rtype: Optional[str]
        """
        return self.read(name)

    def read(self, name: str) -> Optional[str]:
        """Read a raw value from the redis store. (Alias of Redis.get)

        :param name: The name of the key to read from.
        :type name: str
        :return: The raw value as a string, or None if the key does not exist or an error occurs.
        :rtype: Optional[str]
        """
        return self.get(name)

    def read_json(self, name: str) -> Optional[dict]:
        """Read a json value from the redis store.

        :param name: The name of the key to read from.
        :type name: str
        :return: The JSON-decoded value, or None if the key does not exist or an error occurs.
        :rtype: Optional[dict]
        """
        try:
            raw = self.get(name)
            return json.loads(raw) if raw else None
        except Exception as exc:
            if self.on_error:
                self.on_error(exc)
            return None
