"""Synthetic Data Layer - Project 0.

Generates a realistic, reproducible synthetic NZ retail workforce dataset
(employees, stores, leave, rosters, demand, remuneration, calendar).
"""

from .generate import generate_all, generate_synthetic_data

__all__ = ["generate_all", "generate_synthetic_data"]