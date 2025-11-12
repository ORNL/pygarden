#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper mixin to test API using GET/POST tests."""

import requests
import io
from requests_toolbelt.multipart.encoder import MultipartEncoder
from types import FunctionType

class BooleanValue:
    """This is a helper class for bool type responses to match
    a specific `True` or `False` value.

    :param val: Value to validate to
    :type val: bool
    """

    def __init__(self, val: bool):
        """Constructor
        """
        self.val = val
        self.check_val = None
    
    def __str__(self):
        """Creates a string representation of the last checked value

        :return: String representation of last checked value
        :rtype: str
        """
        return str(self.check_val)
    
    def check(self, val):
        """Checks the value passed in with the boolean value that it is
        supposed to match and returns if it is a match

        :raises Exception: Raises exception if the value to check is not a bool
        :return: `True` if the value passed in matches the value set to match
        :rtype: bool
        """
        self.check_val = val
        if isinstance(val, bool):
            return val == self.val
        raise Exception("Return value is not a boolean")


class APITestMixin:
    """"A parent class to have helper functions for the API Testing

    :param api_base: Base API URL to GET/POST to
    :type api_base: str
    """
    
    def __init__(self, api_base: str):
        """Constructor
        """
        self.api_base = api_base
        self.verify_ssl = False

    @staticmethod
    def print_line_separator(width: int = 80):
        """Prints a nice line to separate output sections

        :param width: Number of characters to print for a line,
            defaults to 80
        :type width: int, optional
        """
        print("█"*width, flush=True)
    
    def get(self, uri: str, jwt_token: str = None, access_key: str = None):
        """Calls a GET request to the api_base + the uri passed in.

        :param uri: Suffix to the URL to GET from the API to be added to the api_base
        :type uri: str
        :param jwt_token: JWT to pass in the Authentication header, defaults to None
        :type jwt_token: str, optional
        :param access_key: Token to pass in the access-token header, defaults to None
        :type access_key: str, optional
        :return: The response from the GET request
        :rtype: response
        """
        headers = {}
        if jwt_token != None:
            headers["Authorization"] = f"Bearer {jwt_token}"
        if access_key != None:
            headers["access-token"] = access_key
        response = requests.get(f"{self.api_base}/{uri}", headers=headers, verify=self.verify_ssl)
        response.raise_for_status()
        return response

    def post(self, uri: str, data: dict | MultipartEncoder | io.BytesIO = None, jwt_token: str = None, access_key: str = None):
        """Calls a POST request to the api_base + the uri passed in along with the
        data and any needed header information.

        :param uri: Suffix to the URL to POST from the API to be added to the api_base
        :type uri: str
        :param data: Data to post to the endpoint, defaults to None
        :type data: dict | MultipartEncoder | io.BytesIO, optional
        :param jwt_token: JWT to pass in the Authentication header, defaults to None
        :type jwt_token: str, optional
        :param access_key: Token to pass in the access-token header, defaults to None
        :type access_key: str, optional
        :return: The response from the POST request
        :rtype: response
        """
        headers = { "Content-Type": "application/json" }
        if isinstance(data, MultipartEncoder):
            headers["Content-Type"] = data.content_type
        if jwt_token != None:
            headers["Authorization"] = f"Bearer {jwt_token}"
        if access_key != None:
            headers["access-token"] = access_key
        response = requests.post(f"{self.api_base}/{uri}", data=data, headers=headers, verify=self.verify_ssl)
        response.raise_for_status()
        return response

    def run_test(self, func: FunctionType, output_type: type, success_msg: str, *extra_args):
        """Runs a test and compares the output to the type passed in.

        :param func: Function to call to run a test
        :type func: types.FunctionType
        :param output_type: The output type that the function is supposed to return.
            If the output_type = BooleanValue then it will call the check function
        :type output_type: type
        :param success_msg: Message to print if the test is successful, will replace
            `{VAL}` in the message with the actual value returned
        :type success_msg: str
        :param extra_args: Extra arguments to pass to the test function
        :type extra_args: any
        :return: If the test passes, the return value from the test, otherwise `None`
        :rtype: any
        """
        try:
            val = func(*extra_args)
            if isinstance(output_type, BooleanValue):
                if output_type.check(val):
                    print(success_msg.replace("{VAL}", str(val)), flush=True)
                    return val
                else:
                    print(f"{func.__name__} did not return the right value, it returned {val} instead of {output_type.val}", flush=True)
                    return
            elif isinstance(val, output_type):
                print(success_msg.replace("{VAL}", str(val)), flush=True)
                return val
            print(f"{func.__name__} did not return the right type, it returned {type(val).__name__} instead of {output_type.__name__}", flush=True)
        except Exception as e:
            print(f"{func.__name__} test failed with error: {e}", flush=True)
