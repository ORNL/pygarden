#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT connection and message handling.
"""

import threading
import json
import paho.mqtt.client as mqtt
from typing import Any, Callable, Dict, Optional
from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class MqttBus:
    """
    Provides MQTT connection using environment variables for configuration.
    """
    DEFAULT_HOST = ce("MQTT_HOST", "localhost")
    DEFAULT_PORT = ce("MQTT_PORT", 1883)
    
    DEFAULT_LOG_PATH = ce("MQTT_LOG_FILE", "")
    DEFAULT_LOG_MODE = ce("MQTT_LOG_MODE", "a")
    DEFAULT_LOG_ENCODING = ce("MQTT_LOG_ENCODING", "utf-8")

    def __init__(
        self,
        log_file_info: Optional[dict] = None,
        connection_info: Optional[dict] = None,
        **kwargs: Dict[str, Any],
    ):
        """Create a MQTT object

        This *does not* open a connection to the server.  Use connect() or `with` to establish a connection.

        :param log_file_info: A dictionary containing log file info.
        :param connection_info: A dictionary containing connection info.
        """
        if connection_info is None:
            connection_info = {}
        self.host, self.port = connection_info.get("host", MqttBus.DEFAULT_HOST), connection_info.get("port", MqttBus.DEFAULT_PORT)
        self.client = mqtt.Client(**kwargs)
        
        if log_file_info is None:
            log_file_info = {
                "path": MqttBus.DEFAULT_LOG_PATH,
                "mode": MqttBus.DEFAULT_LOG_MODE,
                "encoding": MqttBus.DEFAULT_LOG_ENCODING,
            }
        if log_file_info["path"] == "":
            self.logger = create_logger()
        else:
            self.logger = create_logger(log_file_info["path"], log_file_info["mode"], log_file_info["encoding"])
        self._routes: dict[str, Callable[[str], None]] = {}

    def route(self, topic: str, handler: Callable[[str], None]) -> None:
        """Register a handler for a specific MQTT topic.

        :param topic: The MQTT topic to subscribe to.
        :type topic: str
        :param handler: A callable that takes a single string argument (the message payload) and handles the message.
        :type handler: Callable[[str], None]
        """
        self._routes[topic] = handler

    def connect(self) -> None:
        """Establish a connection to the MQTT broker and start the message loop."""
        self.client.on_connect = lambda c, u, f, rc: self.logger.info("MQTT connected rc=%s", rc)
        self.client.on_message = self._on_message
        self.client.connect(self.host, self.port)
        for t in self._routes:
            self.client.subscribe(t)
        threading.Thread(target=self.client.loop_forever, daemon=True).start()

    def _on_message(self, _c, _u, msg):
        """Internal function: Handle incoming MQTT messages and dispatch them to the appropriate handler."""
        self.logger.debug("Recieved message for topic: %s", msg.topic)
        payload = msg.payload.decode("utf-8") if msg.payload else ""
        handler = self._routes.get(msg.topic)
        if handler:
            handler(payload)

    def pub(self, topic: str, obj: Any) -> None:
        """Publish a message to a specific MQTT topic.

        :param topic: The MQTT topic to publish to.
        :type topic: str
        :param obj: The message payload to publish. Can be a string, bytes, or any JSON-serializable object.
        :type obj: Any
        """
        self.logger.debug("Publishing message for topic: %s", topic)
        payload = obj if isinstance(obj, (str, bytes)) else json.dumps(obj)
        self.client.publish(topic, payload=payload)
    
    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.client and self.client.is_connected():
            self.client.disconnect()
        self.logger.info("MQTT disconnected")
    
    def __del__(self):
        """
        Close the MQTT connection.

        Note that you *should not* rely on this to close connection; you
        should explicitly use disconnect() to sever the MQTT connection.  That
        is, the python garbage collector is *not guaranteed to run* when
        execution scope would sever the last reference to a MQTT
        object, nor even when the script finishes execution.
        """
        self.disconnect()
    
    def __enter__(self):
        """Allow MQTT to be entered via with."""
        self.connect()
        return self

    def __exit__(self, err_type, err_value, err_traceback):
        """Handle MQTT disconnection when leaving with."""
        self.disconnect()
