"""Validation helpers for the programme.

Provides schema validation for generated DataFrames and lightweight
assertion helpers used across generators and engines.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd


class ValidationError(Exception):
    """Raised when a DataFrame fails schema validation."""


def validate_columns(
    df: pd.DataFrame,
    required: Sequence[str],
    *,
    allow_extra: bool = True,
    context: str = "DataFrame",
) -> None:
    """Validate that a DataFrame contains the required columns.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    required : Sequence[str]
        Column names that must be present.
    allow_extra : bool, optional
        If ``True`` (default), extra columns are permitted. If ``False``,
        any column not in ``required`` raises an error.
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If required columns are missing or unexpected columns are present.
    """
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValidationError(
            f"{context} is missing required columns: {missing}"
        )

    if not allow_extra:
        extra = [c for c in df.columns if c not in required]
        if extra:
            raise ValidationError(
                f"{context} has unexpected columns: {extra}"
            )


def validate_no_duplicates(
    df: pd.DataFrame,
    subset: Sequence[str],
    *,
    context: str = "DataFrame",
) -> None:
    """Validate that rows are unique on the given subset of columns.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    subset : Sequence[str]
        Columns that should form a unique key.
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If duplicate rows exist on the subset.
    """
    dupes = df.duplicated(subset=list(subset), keep=False)
    if dupes.any():
        n = int(dupes.sum())
        raise ValidationError(
            f"{context} contains {n} duplicate rows on key {list(subset)}"
        )


def validate_non_null(
    df: pd.DataFrame,
    columns: Sequence[str],
    *,
    context: str = "DataFrame",
) -> None:
    """Validate that the given columns contain no null values.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    columns : Sequence[str]
        Columns that must be non-null.
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If any null values are found.
    """
    for col in columns:
        n_null = int(df[col].isna().sum())
        if n_null > 0:
            raise ValidationError(
                f"{context} column '{col}' has {n_null} null values"
            )


def validate_value_range(
    df: pd.DataFrame,
    column: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    *,
    context: str = "DataFrame",
) -> None:
    """Validate that a numeric column falls within an optional range.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    column : str
        Column to check.
    min_value : Optional[float], optional
        Inclusive lower bound.
    max_value : Optional[float], optional
        Inclusive upper bound.
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If values fall outside the specified range.
    """
    if min_value is not None:
        below = df[column] < min_value
        if below.any():
            raise ValidationError(
                f"{context} column '{column}' has {int(below.sum())} values below {min_value}"
            )
    if max_value is not None:
        above = df[column] > max_value
        if above.any():
            raise ValidationError(
                f"{context} column '{column}' has {int(above.sum())} values above {max_value}"
            )


def validate_foreign_keys(
    df: pd.DataFrame,
    fk_column: str,
    parent_df: pd.DataFrame,
    parent_column: str,
    *,
    context: str = "DataFrame",
) -> None:
    """Validate that all values in a foreign-key column exist in a parent table.

    Parameters
    ----------
    df : pd.DataFrame
        The child DataFrame.
    fk_column : str
        Foreign-key column in the child.
    parent_df : pd.DataFrame
        The parent DataFrame.
    parent_column : str
        Key column in the parent.
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If orphaned foreign-key values are found.
    """
    parent_values = set(parent_df[parent_column].unique())
    orphans = set(df[fk_column].unique()) - parent_values
    if orphans:
        raise ValidationError(
            f"{context} column '{fk_column}' has orphaned values: {sorted(orphans)[:10]}"
        )


def validate_schema(
    df: pd.DataFrame,
    schema: Dict[str, Dict[str, Any]],
    *,
    context: str = "DataFrame",
) -> None:
    """Validate a DataFrame against a column schema.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    schema : Dict[str, Dict[str, Any]]
        Mapping of column name → spec dict. Supported spec keys:
        ``dtype`` (pandas dtype or Python type), ``required`` (bool),
        ``min`` / ``max`` (numeric bounds), ``unique`` (bool).
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If the DataFrame does not conform to the schema.
    """
    required_cols = [c for c, spec in schema.items() if spec.get("required", True)]
    validate_columns(df, required_cols, allow_extra=True, context=context)

    for col, spec in schema.items():
        if col not in df.columns:
            continue

        dtype = spec.get("dtype")
        if dtype is not None:
            # Check pandas dtype compatibility
            if isinstance(dtype, str):
                actual = df[col].dtype
                # "object" in schema accepts object, str (StringDtype), or any
                # object-derived dtype
                if dtype == "object":
                    if not (actual == object or pd.api.types.is_string_dtype(actual)):
                        raise ValidationError(
                            f"{context} column '{col}' has dtype {actual}, expected {dtype}"
                        )
                elif not pd.api.types.is_dtype_equal(actual, dtype):
                    # Allow numeric coercion for int/float
                    if not (pd.api.types.is_numeric_dtype(df[col]) and dtype in ("int64", "float64")):
                        raise ValidationError(
                            f"{context} column '{col}' has dtype {actual}, expected {dtype}"
                        )

        if spec.get("unique"):
            if df[col].duplicated().any():
                raise ValidationError(
                    f"{context} column '{col}' contains duplicate values"
                )

        if spec.get("min") is not None or spec.get("max") is not None:
            validate_value_range(
                df, col,
                min_value=spec.get("min"),
                max_value=spec.get("max"),
                context=context,
            )


def validate_all(
    df: pd.DataFrame,
    schema: Dict[str, Dict[str, Any]],
    *,
    context: str = "DataFrame",
) -> None:
    """Run the full set of schema validations on a DataFrame.

    Convenience wrapper that validates columns, nulls, uniqueness, and
    value ranges in one call.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to validate.
    schema : Dict[str, Dict[str, Any]]
        Column schema (see :func:`validate_schema`).
    context : str, optional
        Description used in error messages.

    Raises
    ------
    ValidationError
        If any validation fails.
    """
    validate_schema(df, schema, context=context)

    # Non-null check for required columns
    required_cols = [c for c, spec in schema.items() if spec.get("required", True)]
    validate_non_null(df, required_cols, context=context)

    # Uniqueness check
    unique_cols = [c for c, spec in schema.items() if spec.get("unique")]
    if unique_cols:
        validate_no_duplicates(df, unique_cols, context=context)