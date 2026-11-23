"""Shared type aliases for test fixtures."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

AppFactory = Callable[..., FastAPI]
ClientFactory = Callable[..., TestClient]
PathFactory = Callable[[str], Path]
