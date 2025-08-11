#!/usr/bin/env python3
"""
Test script to verify pre-push formatting works correctly.
This file intentionally has formatting issues to test the pre-push hook.
"""

import os
import sys
import json


def test_function(x,y,z):
    """Test function with poor formatting"""
    result=x+y*z
    return result


class TestClass:
    def __init__(self,name,age):
        self.name=name
        self.age=age
    
    def get_info(self):
        return f"Name: {self.name}, Age: {self.age}"


if __name__=="__main__":
    test_obj=TestClass("Test",25)
    print(test_obj.get_info())
    print(test_function(1,2,3))