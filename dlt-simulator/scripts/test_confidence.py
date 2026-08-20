#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for margin_of_error function in confidence.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from confidence import margin_of_error

def test_normal_case():
    """margin_of_error(50, 100, 0.95) should be > 0 and < 0.5"""
    moe = margin_of_error(50, 100, 0.95)
    assert moe > 0, f"Expected > 0, got {moe}"
    assert moe < 0.5, f"Expected < 0.5, got {moe}"
    print(f"PASS: margin_of_error(50, 100, 0.95) = {moe}")

def test_zero_successes():
    """margin_of_error(0, 100, 0.95) should be > 0"""
    moe = margin_of_error(0, 100, 0.95)
    assert moe > 0, f"Expected > 0, got {moe}"
    print(f"PASS: margin_of_error(0, 100, 0.95) = {moe}")

def test_zero_trials():
    """margin_of_error(50, 0, 0.95) should == 0.5"""
    moe = margin_of_error(50, 0, 0.95)
    assert moe == 0.5, f"Expected 0.5, got {moe}"
    print(f"PASS: margin_of_error(50, 0, 0.95) = {moe}")

if __name__ == "__main__":
    test_normal_case()
    test_zero_successes()
    test_zero_trials()
    print("\nAll tests passed!")
