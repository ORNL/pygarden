#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provide a WebSocket Mixing for attaching to Scraping classes."""

import json

import urllib3
from websocket import create_connection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WebsocketMixin:
    """Group together all WebSocket logic into a single Mixin."""

    def request(self, url, **kwargs):
        """
        Create a websocket handshake with optional payload dictionary.

        :param url: WSS schema URL.
        :param send_dict: Python Dictionary to send during connection.
        :param kwargs: Optional parameters for create_connection.
        :returns: WebSocket response data.
        """
        if self.send_dict is not None:
            assert isinstance(self.send_dict, dict)  # make sure we pass a dict
        ws = create_connection(url, timeout=self.timeout, **kwargs)
        ws.send(json.dumps(self.send_dict))
        if self.skip_num == 0:
            result = ws.recv()
        else:
            while self.skip_num > 0:
                result = ws.recv()
                self.skip_num -= 1
        return result
