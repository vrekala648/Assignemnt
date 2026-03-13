"""
main.py
Entry point for the Patient Health Analytics System.

Usage:
    python main.py
"""

import sys
import os

# ── ensure all modules are importable regardless of working directory ──────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── guard against missing tkinter ─────────────────────────────────────────
try:
    import tkinter as tk
except ImportError:
    print(
        "ERROR: tkinter is not available.\n"
        "On Ubuntu/Debian install it with:  sudo apt-get install python3-tk\n"
        "On Windows/macOS it is bundled with the standard Python installer."
    )
    sys.exit(1)

# ── optional matplotlib check ─────────────────────────────────────────────
try:
    import matplotlib  # noqa: F401
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── import application modules ────────────────────────────────────────────
try:
    from load_dataset_module import DatasetLoader, PatientRecord
    from statistics_module   import HealthStatistics
    from query_module        import PatientQuery
    from user_interface_module import PatientHealthApp
except ImportError as e:
    import tkinter.messagebox as mb
    root = tk.Tk(); root.withdraw()
    mb.showerror("Import Error",
                 f"Could not load a required module:\n\n{e}\n\n"
                 "Make sure all five .py files are in the same directory.")
    sys.exit(1)


# ============================================================ #
#   Application controller / orchestrator                      #
# ============================================================ #
class AppController:
    """
    Orchestrates application start-up, optional CLI demo mode,
    and graceful shutdown.
    """

    def __init__(self):
        self.loader = DatasetLoader()
        self.stats  = HealthStatistics(self.loader)

    # ── headless self-test / demo ──────────────────────────────
    def run_demo(self) -> None:
        """
        Generate sample data and print a quick statistical summary.
        Useful for testing the backend without a display.
        """
        print("=" * 60)
        print("  PATIENT HEALTH ANALYTICS SYSTEM — DEMO MODE")
        print("=" * 60)

        demo_path = os.path.join(ROOT, "demo_patients.csv")
        print(f"\n[1] Generating 150 sample patients → {demo_path}")
        self.loader.generate_sample_data(150, demo_path)
        print(f"    {self.loader.count} records loaded.")

        print("\n[2] Descriptive statistics (Age & Heart Rate)")
        for field in ("age", "heart_rate"):
            s = self.stats.field_summary(field)
            print(f"\n    {field.upper()}")
            for k, v in s.items():
                if k != "field":
                    print(f"      {k:<10}: {v}")

        print("\n[3] Top 5 diagnoses")
        for diag, cnt in self.stats.top_diagnoses(5):
            print(f"      {diag:<25} {cnt}")

        print("\n[4] Vital-sign risk summary")
        risk = self.stats.vital_sign_risk_summary()
        print(f"      Hypertension : {risk['hypertension_risk']} ({risk['hypertension_pct']}%)")
        print(f"      Fever        : {risk['fever_cases']} ({risk['fever_pct']}%)")

        print("\n[5] Query — Female patients with Diabetes aged 40–70")
        results = (PatientQuery(self.loader)
                   .by_gender("Female")
                   .by_diagnosis("Diabetes")
                   .age_between(40, 70)
                   .execute())
        print(f"      Found {len(results)} patient(s).")
        for r in results[:5]:
            print(f"        {r.patient_id}  {r.name}  age={r.age}  diag={r.diagnosis}")

        print("\n[6] Critical patients")
        critical = PatientQuery.critical_patients(self.loader)
        print(f"      {len(critical)} patient(s) flagged with critical vital signs.")

        print("\nDemo complete. Run without --demo to launch the GUI.\n")

    # ── GUI launcher ──────────────────────────────────────────────
    def run_gui(self) -> None:
        if not HAS_MPL:
            print("NOTE: matplotlib is not installed — charts will be unavailable.\n"
                  "      Install with: pip install matplotlib")

        app = PatientHealthApp()

        # ── auto-load a CSV passed as first argument ──────────────
        if len(sys.argv) > 1:
            path = sys.argv[1]
            if os.path.isfile(path):
                try:
                    loaded, errors = app.loader.load_csv(path)
                    app._update_status()
                    app._show_page("dashboard")
                    if errors:
                        print(f"Loaded {loaded} records with {len(errors)} error(s).")
                except Exception as e:
                    print(f"Could not auto-load '{path}': {e}")

        app.mainloop()


# ============================================================ #
#   Entry point                                                #
# ============================================================ #
def main():
    controller = AppController()

    if "--demo" in sys.argv:
        controller.run_demo()
    else:
        controller.run_gui()


if __name__ == "__main__":
    main()
