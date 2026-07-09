# -*- coding: utf-8 -*-
"""
Deep Extraction Stub for RenLocalizer Lite.
=========================================

This file stubs out the heavy AST analyzer to avoid dependencies in the Lite version.
"""

class DeepExtractionConfig:
    def __init__(self, *args, **kwargs):
        pass

class DeepVariableAnalyzer:
    def __init__(self, *args, **kwargs):
        pass
    def is_likely_translatable(self, var_name, *args, **kwargs):
        # Fallback default
        return True
    def is_technical_string(self, text, *args, **kwargs):
        return False

class FStringReconstructor:
    def __init__(self, *args, **kwargs):
        pass

class MultiLineStructureParser:
    def __init__(self, *args, **kwargs):
        pass

def confidence_band(*args, **kwargs):
    return (0.0, 1.0)

def resolve_minimum_extraction_confidence(*args, **kwargs):
    return 0.5

def score_extraction_confidence(*args, **kwargs):
    return 1.0

_shared_analyzer = DeepVariableAnalyzer()
