"""Tests for the preprocessing script."""
import pytest
import pandas as pd
import numpy as np
from pipelines.abalone.preprocess import merge_two_dicts

def test_merge_two_dicts():
    """Test the dictionary merging utility function."""
    dict1 = {"a": 1, "b": 2}
    dict2 = {"c": 3, "d": 4}
    merged = merge_two_dicts(dict1, dict2)
    
    # Original dicts should be unchanged
    assert dict1 == {"a": 1, "b": 2}
    assert dict2 == {"c": 3, "d": 4}
    assert merged == {"a": 1, "b": 2, "c": 3, "d": 4}