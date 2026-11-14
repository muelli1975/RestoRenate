"""Locate the shipped code and the portable program's writable folder."""
from pathlib import Path


CODE = Path(__file__).resolve().parent
ROOT = CODE.parent if CODE.name == '_internal' else CODE
