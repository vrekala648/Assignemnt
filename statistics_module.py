"""
statistics_module.py
Computes descriptive statistics and analytics on patient data.
"""

import math
from collections import Counter
from load_dataset_module import DatasetLoader, PatientRecord


class StatisticsError(Exception):
    """Raised when statistics cannot be computed."""


class HealthStatistics:
    """
    Provides statistical analysis methods for a DatasetLoader instance.
    All methods are pure (do not mutate the dataset).
    """

    NUMERIC_FIELDS = ("age", "heart_rate", "blood_pressure_sys",
                      "blood_pressure_dia", "temperature")

    def __init__(self, loader: DatasetLoader):
        if not isinstance(loader, DatasetLoader):
            raise TypeError("Expected a DatasetLoader instance.")
        self._loader = loader

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    def _require_records(self):
        if self._loader.count == 0:
            raise StatisticsError("No patient records loaded.")

    def _extract_numeric(self, field: str) -> list[float]:
        self._require_records()
        if field not in self.NUMERIC_FIELDS:
            raise ValueError(f"'{field}' is not a recognised numeric field. "
                             f"Choose from: {self.NUMERIC_FIELDS}")
        return [getattr(r, field) for r in self._loader.records]

    @staticmethod
    def _mean(values: list[float]) -> float:
        return sum(values) / len(values)

    @staticmethod
    def _median(values: list[float]) -> float:
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2

    @staticmethod
    def _mode(values: list[float]) -> float:
        counts = Counter(values)
        return counts.most_common(1)[0][0]

    @staticmethod
    def _std(values: list[float], mean: float) -> float:
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _percentile(values: list[float], p: float) -> float:
        s = sorted(values)
        n = len(s)
        idx = (p / 100) * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return s[lo] + (s[hi] - s[lo]) * (idx - lo)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def field_summary(self, field: str) -> dict:
        """Return a full descriptive stats dict for a numeric field."""
        values = self._extract_numeric(field)
        mean = self._mean(values)
        return {
            "field": field,
            "count": len(values),
            "mean": round(mean, 2),
            "median": round(self._median(values), 2),
            "mode": round(self._mode(values), 2),
            "std_dev": round(self._std(values, mean), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "range": round(max(values) - min(values), 2),
            "q1": round(self._percentile(values, 25), 2),
            "q3": round(self._percentile(values, 75), 2),
            "iqr": round(self._percentile(values, 75) - self._percentile(values, 25), 2),
        }

    def all_fields_summary(self) -> list[dict]:
        """Return field_summary for every numeric field."""
        return [self.field_summary(f) for f in self.NUMERIC_FIELDS]

    # ---- Categorical distributions ------------------------------------ #
    def gender_distribution(self) -> dict[str, int]:
        self._require_records()
        return dict(Counter(r.gender for r in self._loader.records))

    def blood_group_distribution(self) -> dict[str, int]:
        self._require_records()
        return dict(Counter(r.blood_group for r in self._loader.records))

    def diagnosis_distribution(self) -> dict[str, int]:
        self._require_records()
        return dict(Counter(r.diagnosis for r in self._loader.records)
                    .most_common())

    def status_distribution(self) -> dict[str, int]:
        self._require_records()
        return dict(Counter(r.status for r in self._loader.records))

    # ---- Age groups --------------------------------------------------- #
    def age_group_distribution(self) -> dict[str, int]:
        self._require_records()
        groups: dict[str, int] = {
            "0–17 (Child)": 0,
            "18–35 (Young Adult)": 0,
            "36–59 (Middle-Aged)": 0,
            "60–79 (Senior)": 0,
            "80+ (Elderly)": 0,
        }
        for r in self._loader.records:
            if r.age <= 17:
                groups["0–17 (Child)"] += 1
            elif r.age <= 35:
                groups["18–35 (Young Adult)"] += 1
            elif r.age <= 59:
                groups["36–59 (Middle-Aged)"] += 1
            elif r.age <= 79:
                groups["60–79 (Senior)"] += 1
            else:
                groups["80+ (Elderly)"] += 1
        return groups

    # ---- Vital signs risk flags --------------------------------------- #
    def vital_sign_risk_summary(self) -> dict:
        """Classify each patient's vitals into normal/elevated/high-risk."""
        self._require_records()
        records = self._loader.records
        total = len(records)

        high_bp = sum(1 for r in records if r.blood_pressure_sys >= 140 or r.blood_pressure_dia >= 90)
        low_bp = sum(1 for r in records if r.blood_pressure_sys < 90)
        high_hr = sum(1 for r in records if r.heart_rate > 100)
        low_hr = sum(1 for r in records if r.heart_rate < 60)
        fever = sum(1 for r in records if r.temperature >= 38.0)
        hypothermia = sum(1 for r in records if r.temperature < 36.0)

        return {
            "total_patients": total,
            "hypertension_risk": high_bp,
            "hypertension_pct": round(high_bp / total * 100, 1),
            "hypotension_risk": low_bp,
            "hypotension_pct": round(low_bp / total * 100, 1),
            "tachycardia_risk": high_hr,
            "tachycardia_pct": round(high_hr / total * 100, 1),
            "bradycardia_risk": low_hr,
            "bradycardia_pct": round(low_hr / total * 100, 1),
            "fever_cases": fever,
            "fever_pct": round(fever / total * 100, 1),
            "hypothermia_cases": hypothermia,
            "hypothermia_pct": round(hypothermia / total * 100, 1),
        }

    # ---- Correlations ------------------------------------------------- #
    def correlation(self, field_a: str, field_b: str) -> float:
        """Pearson correlation coefficient between two numeric fields."""
        a_vals = self._extract_numeric(field_a)
        b_vals = self._extract_numeric(field_b)
        n = len(a_vals)
        if n < 2:
            raise StatisticsError("Need at least 2 records for correlation.")
        mean_a, mean_b = self._mean(a_vals), self._mean(b_vals)
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(a_vals, b_vals))
        std_a = self._std(a_vals, mean_a)
        std_b = self._std(b_vals, mean_b)
        if std_a == 0 or std_b == 0:
            return 0.0
        return round(cov / (n * std_a * std_b), 4)

    def correlation_matrix(self) -> dict[str, dict[str, float]]:
        """Full correlation matrix for all numeric fields."""
        fields = self.NUMERIC_FIELDS
        return {
            fa: {fb: self.correlation(fa, fb) for fb in fields}
            for fa in fields
        }

    # ---- Admission trends --------------------------------------------- #
    def monthly_admissions(self) -> dict[str, int]:
        """Count admissions per YYYY-MM."""
        self._require_records()
        counter: Counter = Counter()
        for r in self._loader.records:
            month = r.admission_date[:7]  # "YYYY-MM"
            counter[month] += 1
        return dict(sorted(counter.items()))

    # ---- Top diagnoses ------------------------------------------------- #
    def top_diagnoses(self, n: int = 5) -> list[tuple[str, int]]:
        self._require_records()
        return Counter(r.diagnosis for r in self._loader.records).most_common(n)

    # ---- Average vitals by diagnosis ---------------------------------- #
    def avg_vitals_by_diagnosis(self) -> dict[str, dict[str, float]]:
        self._require_records()
        groups: dict[str, list[PatientRecord]] = {}
        for r in self._loader.records:
            groups.setdefault(r.diagnosis, []).append(r)
        result = {}
        for diag, patients in groups.items():
            n = len(patients)
            result[diag] = {
                "count": n,
                "avg_age": round(sum(p.age for p in patients) / n, 1),
                "avg_hr": round(sum(p.heart_rate for p in patients) / n, 1),
                "avg_bp_sys": round(sum(p.blood_pressure_sys for p in patients) / n, 1),
                "avg_temp": round(sum(p.temperature for p in patients) / n, 1),
            }
        return result
