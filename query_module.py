"""
query_module.py
Provides flexible search and filtering on a DatasetLoader.
"""

from __future__ import annotations
from typing import Callable
from load_dataset_module import DatasetLoader, PatientRecord


class QueryError(Exception):
    """Raised for invalid query parameters."""


class PatientQuery:
    """
    Fluent query builder for patient records.

    Usage example:
        results = (PatientQuery(loader)
                   .by_gender("Female")
                   .age_between(30, 60)
                   .by_diagnosis("Diabetes")
                   .execute())
    """

    def __init__(self, loader: DatasetLoader):
        if not isinstance(loader, DatasetLoader):
            raise TypeError("Expected a DatasetLoader instance.")
        self._loader = loader
        self._filters: list[Callable[[PatientRecord], bool]] = []

    # ------------------------------------------------------------------ #
    #  Filter builders                                                     #
    # ------------------------------------------------------------------ #
    def _add(self, fn: Callable[[PatientRecord], bool]) -> "PatientQuery":
        self._filters.append(fn)
        return self

    def by_id(self, patient_id: str) -> "PatientQuery":
        """Exact match on patient_id."""
        return self._add(lambda r, pid=patient_id: r.patient_id == pid.strip())

    def by_name(self, name: str, exact: bool = False) -> "PatientQuery":
        """Case-insensitive name search (substring unless exact=True)."""
        n = name.strip().lower()
        if exact:
            return self._add(lambda r: r.name.lower() == n)
        return self._add(lambda r: n in r.name.lower())

    def by_gender(self, gender: str) -> "PatientQuery":
        g = gender.strip().capitalize()
        return self._add(lambda r: r.gender == g)

    def by_blood_group(self, blood_group: str) -> "PatientQuery":
        bg = blood_group.strip().upper()
        return self._add(lambda r: r.blood_group == bg)

    def by_diagnosis(self, diagnosis: str, exact: bool = False) -> "PatientQuery":
        d = diagnosis.strip().lower()
        if exact:
            return self._add(lambda r: r.diagnosis.lower() == d)
        return self._add(lambda r: d in r.diagnosis.lower())

    def by_status(self, status: str, exact: bool = False) -> "PatientQuery":
        s = status.strip().lower()
        if exact:
            return self._add(lambda r: r.status.lower() == s)
        return self._add(lambda r: s in r.status.lower())

    def age_between(self, low: int, high: int) -> "PatientQuery":
        if low > high:
            raise QueryError(f"age_between: low ({low}) > high ({high}).")
        return self._add(lambda r, lo=low, hi=high: lo <= r.age <= hi)

    def heart_rate_between(self, low: float, high: float) -> "PatientQuery":
        if low > high:
            raise QueryError(f"heart_rate_between: low ({low}) > high ({high}).")
        return self._add(lambda r, lo=low, hi=high: lo <= r.heart_rate <= hi)

    def bp_systolic_above(self, threshold: float) -> "PatientQuery":
        return self._add(lambda r, t=threshold: r.blood_pressure_sys > t)

    def bp_diastolic_above(self, threshold: float) -> "PatientQuery":
        return self._add(lambda r, t=threshold: r.blood_pressure_dia > t)

    def temperature_above(self, threshold: float) -> "PatientQuery":
        return self._add(lambda r, t=threshold: r.temperature > t)

    def temperature_between(self, low: float, high: float) -> "PatientQuery":
        if low > high:
            raise QueryError(f"temperature_between: low ({low}) > high ({high}).")
        return self._add(lambda r, lo=low, hi=high: lo <= r.temperature <= hi)

    def admitted_after(self, date_str: str) -> "PatientQuery":
        """Filter by admission date (inclusive). Date format: YYYY-MM-DD."""
        return self._add(lambda r, d=date_str: r.admission_date >= d)

    def admitted_before(self, date_str: str) -> "PatientQuery":
        """Filter by admission date (inclusive). Date format: YYYY-MM-DD."""
        return self._add(lambda r, d=date_str: r.admission_date <= d)

    def custom(self, fn: Callable[[PatientRecord], bool]) -> "PatientQuery":
        """Apply an arbitrary filter function."""
        return self._add(fn)

    # ------------------------------------------------------------------ #
    #  Execution                                                           #
    # ------------------------------------------------------------------ #
    def execute(self) -> list[PatientRecord]:
        """Run all accumulated filters and return matching records."""
        results = self._loader.records
        for f in self._filters:
            results = [r for r in results if f(r)]
        return results

    def count(self) -> int:
        """Return the number of records that match the current filters."""
        return len(self.execute())

    def reset(self) -> "PatientQuery":
        """Clear all filters."""
        self._filters.clear()
        return self

    # ------------------------------------------------------------------ #
    #  Sorting helpers                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def sort_records(
        records: list[PatientRecord],
        field: str,
        ascending: bool = True
    ) -> list[PatientRecord]:
        """Sort a list of PatientRecord objects by a named field."""
        valid = {
            "patient_id", "name", "age", "gender", "blood_group",
            "diagnosis", "heart_rate", "blood_pressure_sys",
            "blood_pressure_dia", "temperature", "admission_date", "status"
        }
        if field not in valid:
            raise QueryError(f"Cannot sort by '{field}'. Valid fields: {valid}")
        return sorted(records, key=lambda r: getattr(r, field), reverse=not ascending)

    # ------------------------------------------------------------------ #
    #  Convenience class-methods                                           #
    # ------------------------------------------------------------------ #
    @classmethod
    def critical_patients(cls, loader: DatasetLoader) -> list[PatientRecord]:
        """Return patients with any critical vital sign."""
        return (cls(loader)
                .custom(lambda r: (r.blood_pressure_sys >= 160
                                   or r.blood_pressure_dia >= 100
                                   or r.heart_rate > 120
                                   or r.heart_rate < 50
                                   or r.temperature >= 39.5
                                   or r.temperature < 35.5))
                .execute())

    @classmethod
    def search_all_fields(cls, loader: DatasetLoader, term: str) -> list[PatientRecord]:
        """Full-text search across id, name, diagnosis, status, blood_group, gender."""
        t = term.strip().lower()
        return (cls(loader)
                .custom(lambda r: (
                    t in r.patient_id.lower()
                    or t in r.name.lower()
                    or t in r.diagnosis.lower()
                    or t in r.status.lower()
                    or t in r.blood_group.lower()
                    or t in r.gender.lower()
                ))
                .execute())
