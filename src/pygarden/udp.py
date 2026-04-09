#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP connection and message handling.
"""

import socket
import queue
import threading
from typing import Any, Dict, Optional
from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

class Udp:
    """
    Provides UDP connection using environment variables for configuration.
    """
    DEFAULT_SEND_HOST = ce("UDP_SEND_HOST", "localhost")
    DEFAULT_SEND_PORT = ce("UDP_SEND_PORT", None)
    DEFAULT_RECIEVE_HOST = ce("UDP_RECIEVE_HOST", "0.0.0.0")
    DEFAULT_RECIEVE_PORT = ce("UDP_RECIEVE_PORT", None)
    
    DEFAULT_LOG_PATH = ce("UDP_LOG_FILE", "")
    DEFAULT_LOG_MODE = ce("UDP_LOG_MODE", "a")
    DEFAULT_LOG_ENCODING = ce("UDP_LOG_ENCODING", "utf-8")

    def __init__(
        self,
        log_file_info: Optional[dict] = None,
        connection_info: Optional[dict] = None,
        data_received: Optional[callable] = None,
        **kwargs: Dict[str, Any],
    ):
        """Create a UDP object

        :param log_file_info: A dictionary containing log file info.
        :param connection_info: A dictionary containing connection info.
        :param data_received: A callback function to handle received data.
        """
        self.data_received = data_received
        if connection_info is None:
            connection_info = {}
        self.send_host = connection_info.get("send_host", Udp.DEFAULT_SEND_HOST)
        self.send_port = connection_info.get("send_port", Udp.DEFAULT_SEND_PORT)
        self.receive_host = connection_info.get("receive_host", Udp.DEFAULT_RECIEVE_HOST)
        self.receive_port = connection_info.get("receive_port", Udp.DEFAULT_RECIEVE_PORT)
        
        if log_file_info is None:
            log_file_info = {
                "path": Udp.DEFAULT_LOG_PATH,
                "mode": Udp.DEFAULT_LOG_MODE,
                "encoding": Udp.DEFAULT_LOG_ENCODING,
            }
        if log_file_info["path"] == "":
            self.logger = create_logger()
        else:
            self.logger = create_logger(log_file_info["path"], log_file_info["mode"], log_file_info["encoding"])
        
        if self.send_port is not None:
            self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_queue = queue.Queue()

        if self.receive_port is not None:
            self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.receive_socket.bind((self.receive_host, self.receive_port))
            self.receive_socket.settimeout(0.5)
        
        self.stop_event = None
    
    def set_stop_event(self, stop_event: threading.Event) -> None:
        """Set the stop event for the UDP threads.

        :param stop_event: Event to signal the threads to stop.
        :type stop_event: threading.Event
        """
        self.stop_event = stop_event

    def send(self, data: bytes) -> None:
        """Send data to the configured UDP host and port.

        :param data: The data to send.
        :type data: bytes
        """
        if self.send_host is None or self.send_port is None:
            self.logger.error("UDP send host or port not configured")
            return
        self.send_queue.put(data)
    
    def sender_thread(self, stop_event: threading.Event | None = None) -> None:
        """Thread to send outbound UDP messages from the queue.

        :param stop_event: Event to signal the thread to stop.
        :type stop_event: threading.Event
        """
        if not hasattr(self, "send_socket"):
            self.logger.error("UDP send socket not initialized")
            return
        if stop_event is not None:
            self.stop_event = stop_event
        while self.stop_event is None or not self.stop_event.is_set():
            try:
                data = self.send_queue.get(timeout=0.5)
            except socket.timeout:
                # Timeout is expected - allows checking stop_event
                continue
            except queue.Empty:
                continue
            if data:
                try:
                    self.send_socket.sendto(data, (self.send_host, self.send_port))
                    self.logger.debug("Sent UDP data to %s:%s", self.send_host, self.send_port)
                except OSError as e:
                    self.logger.error("Error sending UDP data: %s", e)
    
    def receiver_thread(self, stop_event: threading.Event | None = None) -> None:
        """Thread to receive inbound UDP messages.

        :param stop_event: Event to signal the thread to stop.
        :type stop_event: threading.Event
        """
        if not hasattr(self, "receive_socket"):
            self.logger.error("UDP receive socket not initialized")
            return
        if stop_event is not None:
            self.stop_event = stop_event
        while self.stop_event is None or not self.stop_event.is_set():
            try:
                data, addr = self.receive_socket.recvfrom(2048)
                self.logger.debug("Received UDP data from %s:%s", addr[0], addr[1])
                if self.data_received is not None:
                    self.data_received(data, addr)
            except OSError as e:
                self.logger.error("Error receiving UDP data: %s", e)

