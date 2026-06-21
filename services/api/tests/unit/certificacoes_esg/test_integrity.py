import json
import pytest
from certificacoes_esg.integrity import canonical_json, calculate_snapshot_hash, verify_snapshot_hash

def test_canonical_json_ordering():
    payload1 = {"b": 2, "a": 1, "c": 3}
    payload2 = {"c": 3, "b": 2, "a": 1}
    
    assert canonical_json(payload1) == canonical_json(payload2)
    assert canonical_json(payload1) == '{"a":1,"b":2,"c":3}'

def test_canonical_json_spacing():
    payload = {"key": "value", "list": [1, 2, 3]}
    canonical = canonical_json(payload)
    assert " " not in canonical
    assert canonical == '{"key":"value","list":[1,2,3]}'

def test_canonical_json_none():
    assert canonical_json(None) == "{}"

def test_calculate_snapshot_hash():
    payload = {"hello": "world"}
    hash1 = calculate_snapshot_hash(payload)
    
    payload2 = {"hello": "world"}
    hash2 = calculate_snapshot_hash(payload2)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length

def test_calculate_snapshot_hash_different():
    hash1 = calculate_snapshot_hash({"a": 1})
    hash2 = calculate_snapshot_hash({"a": 2})
    assert hash1 != hash2

def test_verify_snapshot_hash_valid():
    payload = {"data": "test"}
    valid_hash = calculate_snapshot_hash(payload)
    assert verify_snapshot_hash(payload, valid_hash) is True

def test_verify_snapshot_hash_invalid():
    payload = {"data": "test"}
    valid_hash = calculate_snapshot_hash(payload)
    assert verify_snapshot_hash({"data": "test2"}, valid_hash) is False
    assert verify_snapshot_hash(payload, "invalidhash") is False
    assert verify_snapshot_hash(payload, None) is False
    assert verify_snapshot_hash(payload, "") is False
