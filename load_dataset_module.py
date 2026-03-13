"""
load_dataset_module.py
Handles loading, saving, and managing patient datasets.
"""

import csv
import json
import os
import random
from datetime import datetime, timedelta


class PatientRecord:
    """Represents a single patient record."""

    VALID_GENDERS = {"Male", "Female", "Other"}
    VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

    def __init__(self, patient_id, name, age, gender, blood_group,
                 diagnosis, heart_rate, blood_pressure_sys,
                 blood_pressure_dia, temperature, admission_date, status):
        self.patient_id = self._validate_id(patient_id)
        self.name = self._validate_name(name)
        self.age = self._validate_age(age)
        self.gender = self._validate_gender(gender)
        self.blood_group = self._validate_blood_group(blood_group)
        self.diagnosis = str(diagnosis).strip()
        self.heart_rate = self._validate_positive_float(heart_rate, "Heart Rate")
        self.blood_pressure_sys = self._validate_positive_float(blood_pressure_sys, "BP Systolic")
        self.blood_pressure_dia = self._validate_positive_float(blood_pressure_dia, "BP Diastolic")
        self.temperature = self._validate_temperature(temperature)
        self.admission_date = self._validate_date(admission_date)
        self.status = str(status).strip()

    def _validate_id(self, pid):
        pid = str(pid).strip()
        if not pid:
            raise ValueError("Patient ID cannot be empty.")
        return pid

    def _validate_name(self, name):
        name = str(name).strip()
        if not name:
            raise ValueError("Patient name cannot be empty.")
        return name

    def _validate_age(self, age):
        try:
            age = int(age)
            if not (0 <= age <= 130):
                raise ValueError(f"Age {age} is out of valid range (0–130).")
            return age
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid age value: {age}. {e}")

    def _validate_gender(self, gender):
        gender = str(gender).strip().capitalize()
        # Normalize common variants
        mapping = {"M": "Male", "F": "Female", "O": "Other",
                   "male": "Male", "female": "Female", "other": "Other"}
        gender = mapping.get(gender, gender)
        if gender not in self.VALID_GENDERS:
            raise ValueError(f"Invalid gender '{gender}'. Must be one of {self.VALID_GENDERS}.")
        return gender

    def _validate_blood_group(self, bg):
        bg = str(bg).strip().upper()
        if bg not in self.VALID_BLOOD_GROUPS:
            raise ValueError(f"Invalid blood group '{bg}'. Must be one of {self.VALID_BLOOD_GROUPS}.")
        return bg

    def _validate_positive_float(self, value, field):
        try:
            v = float(value)
            if v <= 0:
                raise ValueError(f"{field} must be positive.")
            return round(v, 2)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {field} value: {value}")

    def _validate_temperature(self, temp):
        try:
            temp = float(temp)
            if not (30.0 <= temp <= 45.0):
                raise ValueError(f"Temperature {temp}°C seems implausible (30–45 expected).")
            return round(temp, 1)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid temperature value: {temp}")

    def _validate_date(self, date_str):
        date_str = str(date_str).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Unrecognised date format: '{date_str}'. Use YYYY-MM-DD.")

    def to_dict(self):
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "blood_group": self.blood_group,
            "diagnosis": self.diagnosis,
            "heart_rate": self.heart_rate,
            "blood_pressure_sys": self.blood_pressure_sys,
            "blood_pressure_dia": self.blood_pressure_dia,
            "temperature": self.temperature,
            "admission_date": self.admission_date,
            "status": self.status,
        }

    def __repr__(self):
        return (f"PatientRecord(id={self.patient_id}, name={self.name}, "
                f"age={self.age}, diagnosis={self.diagnosis})")


class DatasetLoader:
    """Loads, saves, and manages a collection of PatientRecord objects."""

    CSV_FIELDS = [
        "patient_id", "name", "age", "gender", "blood_group", "diagnosis",
        "heart_rate", "blood_pressure_sys", "blood_pressure_dia",
        "temperature", "admission_date", "status"
    ]

    def __init__(self):
        self._records: list[PatientRecord] = []
        self._filepath: str | None = None

    # ------------------------------------------------------------------ #
    #  Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def records(self) -> list[PatientRecord]:
        return list(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def filepath(self) -> str | None:
        return self._filepath

    # ------------------------------------------------------------------ #
    #  Loading                                                             #
    # ------------------------------------------------------------------ #
    def load_csv(self, filepath: str) -> tuple[int, list[str]]:
        """Load records from a CSV file. Returns (loaded_count, errors)."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        self._records.clear()
        errors = []
        loaded = 0

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = set(self.CSV_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV is missing required columns: {missing}")

            for line_no, row in enumerate(reader, start=2):
                try:
                    record = PatientRecord(
                        patient_id=row["patient_id"],
                        name=row["name"],
                        age=row["age"],
                        gender=row["gender"],
                        blood_group=row["blood_group"],
                        diagnosis=row["diagnosis"],
                        heart_rate=row["heart_rate"],
                        blood_pressure_sys=row["blood_pressure_sys"],
                        blood_pressure_dia=row["blood_pressure_dia"],
                        temperature=row["temperature"],
                        admission_date=row["admission_date"],
                        status=row["status"],
                    )
                    self._records.append(record)
                    loaded += 1
                except (ValueError, KeyError) as e:
                    errors.append(f"Line {line_no}: {e}")

        self._filepath = filepath
        return loaded, errors

    def load_json(self, filepath: str) -> tuple[int, list[str]]:
        """Load records from a JSON file. Returns (loaded_count, errors)."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        self._records.clear()
        errors = []
        loaded = 0

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of patient objects.")

        for idx, item in enumerate(data):
            try:
                record = PatientRecord(**{k: item[k] for k in self.CSV_FIELDS})
                self._records.append(record)
                loaded += 1
            except (ValueError, KeyError, TypeError) as e:
                errors.append(f"Record {idx + 1}: {e}")

        self._filepath = filepath
        return loaded, errors

    # ------------------------------------------------------------------ #
    #  Saving                                                              #
    # ------------------------------------------------------------------ #
    def save_csv(self, filepath: str) -> None:
        """Save current records to a CSV file."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            writer.writeheader()
            for record in self._records:
                writer.writerow(record.to_dict())
        self._filepath = filepath

    def save_json(self, filepath: str) -> None:
        """Save current records to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2)
        self._filepath = filepath

    # ------------------------------------------------------------------ #
    #  CRUD                                                                #
    # ------------------------------------------------------------------ #
    def add_record(self, record: PatientRecord) -> None:
        if any(r.patient_id == record.patient_id for r in self._records):
            raise ValueError(f"Patient ID '{record.patient_id}' already exists.")
        self._records.append(record)

    def update_record(self, patient_id: str, updated: PatientRecord) -> None:
        for i, r in enumerate(self._records):
            if r.patient_id == patient_id:
                self._records[i] = updated
                return
        raise KeyError(f"Patient ID '{patient_id}' not found.")

    def delete_record(self, patient_id: str) -> None:
        original = len(self._records)
        self._records = [r for r in self._records if r.patient_id != patient_id]
        if len(self._records) == original:
            raise KeyError(f"Patient ID '{patient_id}' not found.")

    def get_record(self, patient_id: str) -> PatientRecord:
        for r in self._records:
            if r.patient_id == patient_id:
                return r
        raise KeyError(f"Patient ID '{patient_id}' not found.")

    # ------------------------------------------------------------------ #
    #  Demo data generator                                                 #
    # ------------------------------------------------------------------ #
    def generate_sample_data(self, n: int = 100, filepath: str = "patients.csv") -> str:
        """Generate n random patient records and save to filepath."""
        diagnoses = [
            "Hypertension", "Diabetes Type 2", "Asthma", "Pneumonia",
            "Appendicitis", "Fracture", "Migraine", "Anaemia",
            "Gastritis", "COVID-19", "Heart Failure", "Kidney Stones",
            "Arthritis", "Depression", "Obesity"
        ]
        statuses = ["Admitted", "Discharged", "Under Observation", "Critical", "Stable"]
        blood_groups = list(PatientRecord.VALID_BLOOD_GROUPS)
        genders = ["Male", "Female", "Other"]
        base_date = datetime(2023, 1, 1)

        self._records.clear()
        for i in range(1, n + 1):
            age = random.randint(5, 90)
            bp_sys = random.randint(90, 180)
            bp_dia = random.randint(60, 110)
            adm = base_date + timedelta(days=random.randint(0, 700))
            record = PatientRecord(
                patient_id=f"P{i:04d}",
                name=f"Patient {i}",
                age=age,
                gender=random.choice(genders),
                blood_group=random.choice(blood_groups),
                diagnosis=random.choice(diagnoses),
                heart_rate=random.randint(55, 120),
                blood_pressure_sys=bp_sys,
                blood_pressure_dia=bp_dia,
                temperature=round(random.uniform(36.0, 40.5), 1),
                admission_date=adm.strftime("%Y-%m-%d"),
                status=random.choice(statuses),
            )
            self._records.append(record)

        self.save_csv(filepath)
        return filepath
