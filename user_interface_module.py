"""
user_interface_module.py
Full tkinter GUI for the Patient Health Analytics System.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import sys

# ── runtime imports (resolved by main.py after path is set) ──────────────
from load_dataset_module import DatasetLoader, PatientRecord
from statistics_module import HealthStatistics
from query_module import PatientQuery

# ── optional matplotlib ──────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB = True
except ImportError:
    MATPLOTLIB = False

# ============================================================ #
#   Colour / style palette                                     #
# ============================================================ #
PALETTE = {
    "bg": "#1C2333",
    "sidebar": "#111827",
    "card": "#243046",
    "accent": "#3B82F6",
    "accent2": "#10B981",
    "accent3": "#F59E0B",
    "danger": "#EF4444",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "entry_bg": "#0F172A",
    "border": "#334155",
    "row_even": "#1E2D45",
    "row_odd": "#1A2535",
    "header": "#1E3A5F",
}

FONT_HEAD = ("Segoe UI", 18, "bold")
FONT_SUB  = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 10)


# ============================================================ #
#   Helper widgets                                             #
# ============================================================ #
class _Card(tk.Frame):
    def __init__(self, parent, title="", **kw):
        kw.setdefault("bg", PALETTE["card"])
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)
        if title:
            tk.Label(self, text=title, bg=PALETTE["card"],
                     fg=PALETTE["accent"], font=FONT_SUB).pack(anchor="w", padx=12, pady=(10, 4))


class _StatBadge(tk.Frame):
    def __init__(self, parent, label, value, color=None):
        color = color or PALETTE["accent"]
        super().__init__(parent, bg=PALETTE["card"], padx=12, pady=8)
        tk.Label(self, text=str(value), bg=PALETTE["card"],
                 fg=color, font=("Segoe UI", 22, "bold")).pack()
        tk.Label(self, text=label, bg=PALETTE["card"],
                 fg=PALETTE["text_muted"], font=("Segoe UI", 9)).pack()


# ============================================================ #
#   Main application window                                    #
# ============================================================ #
class PatientHealthApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Patient Health Analytics System")
        self.geometry("1280x780")
        self.minsize(960, 640)
        self.configure(bg=PALETTE["bg"])

        self.loader = DatasetLoader()
        self.stats  = HealthStatistics(self.loader)

        self._build_ui()
        self._show_page("dashboard")

    # ============================================================ #
    #   Layout                                                     #
    # ============================================================ #
    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────
        top = tk.Frame(self, bg=PALETTE["sidebar"], height=52)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(top, text=" 🏥 Patient Health Analytics System",
                 bg=PALETTE["sidebar"], fg=PALETTE["text"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)

        self._status_var = tk.StringVar(value="No dataset loaded")
        tk.Label(top, textvariable=self._status_var,
                 bg=PALETTE["sidebar"], fg=PALETTE["text_muted"],
                 font=FONT_BODY).pack(side="right", padx=16)

        # ── sidebar + content ─────────────────────────────────────
        body = tk.Frame(self, bg=PALETTE["bg"])
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=PALETTE["sidebar"], width=190)
        sidebar.pack(fill="y", side="left")
        sidebar.pack_propagate(False)

        self._content = tk.Frame(body, bg=PALETTE["bg"])
        self._content.pack(fill="both", expand=True)

        self._pages: dict[str, tk.Frame] = {}
        self._build_sidebar(sidebar)
        self._build_pages()

    def _build_sidebar(self, sidebar):
        tk.Label(sidebar, text="NAVIGATION", bg=PALETTE["sidebar"],
                 fg=PALETTE["text_muted"], font=("Segoe UI", 8, "bold")).pack(
                     anchor="w", padx=14, pady=(18, 6))

        nav_items = [
            ("dashboard",   "📊  Dashboard"),
            ("patients",    "👤  Patients"),
            ("query",       "🔍  Query / Filter"),
            ("statistics",  "📈  Statistics"),
            ("charts",      "🗂  Charts"),
            ("add_patient", "➕  Add Patient"),
        ]
        self._nav_btns: dict[str, tk.Button] = {}
        for key, label in nav_items:
            btn = tk.Button(
                sidebar, text=label, anchor="w",
                bg=PALETTE["sidebar"], fg=PALETTE["text"],
                font=FONT_BODY, bd=0, padx=16, pady=10,
                activebackground=PALETTE["accent"],
                activeforeground="#fff",
                cursor="hand2",
                command=lambda k=key: self._show_page(k)
            )
            btn.pack(fill="x")
            self._nav_btns[key] = btn

        # ── file ops ─────────────────────────────────────────────
        tk.Frame(sidebar, bg=PALETTE["border"], height=1).pack(
            fill="x", padx=10, pady=12)

        tk.Label(sidebar, text="FILE OPS", bg=PALETTE["sidebar"],
                 fg=PALETTE["text_muted"], font=("Segoe UI", 8, "bold")).pack(
                     anchor="w", padx=14, pady=(0, 4))

        for label, cmd in [
            ("📂  Load CSV",    self._load_csv),
            ("📂  Load JSON",   self._load_json),
            ("💾  Save CSV",    self._save_csv),
            ("💾  Save JSON",   self._save_json),
            ("🎲  Sample Data", self._gen_sample),
        ]:
            tk.Button(
                sidebar, text=label, anchor="w",
                bg=PALETTE["sidebar"], fg=PALETTE["text"],
                font=FONT_BODY, bd=0, padx=16, pady=8,
                activebackground=PALETTE["accent2"],
                activeforeground="#fff",
                cursor="hand2", command=cmd
            ).pack(fill="x")

    # ============================================================ #
    #   Pages                                                      #
    # ============================================================ #
    def _build_pages(self):
        self._pages["dashboard"]   = self._build_dashboard()
        self._pages["patients"]    = self._build_patients()
        self._pages["query"]       = self._build_query()
        self._pages["statistics"]  = self._build_statistics()
        self._pages["charts"]      = self._build_charts()
        self._pages["add_patient"] = self._build_add_patient()

    def _show_page(self, key: str):
        for k, p in self._pages.items():
            p.place_forget()
        self._pages[key].place(relx=0, rely=0, relwidth=1, relheight=1)

        # Highlight active nav btn
        for k, btn in self._nav_btns.items():
            btn.configure(bg=PALETTE["accent"] if k == key else PALETTE["sidebar"])

        # Refresh dynamic pages
        if key == "dashboard":
            self._refresh_dashboard()
        elif key == "patients":
            self._refresh_patient_table()
        elif key == "statistics":
            self._refresh_statistics()

    # ─── Dashboard ───────────────────────────────────────────────
    def _build_dashboard(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])

        tk.Label(page, text="Dashboard Overview",
                 bg=PALETTE["bg"], fg=PALETTE["text"], font=FONT_HEAD).pack(
                     anchor="w", padx=24, pady=(20, 4))
        tk.Label(page, text="Summary statistics at a glance",
                 bg=PALETTE["bg"], fg=PALETTE["text_muted"], font=FONT_BODY).pack(
                     anchor="w", padx=24)

        self._dash_badges = tk.Frame(page, bg=PALETTE["bg"])
        self._dash_badges.pack(fill="x", padx=20, pady=16)

        self._dash_text = tk.Text(page, bg=PALETTE["card"], fg=PALETTE["text"],
                                   font=FONT_MONO, relief="flat", bd=0,
                                   wrap="word", state="disabled", height=18)
        self._dash_text.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        return page

    def _refresh_dashboard(self):
        # Clear badges
        for w in self._dash_badges.winfo_children():
            w.destroy()

        if self.loader.count == 0:
            _StatBadge(self._dash_badges, "Patients", "—").pack(side="left", padx=8)
            self._dash_write("Load a dataset to see analytics.")
            return

        risk = self.stats.vital_sign_risk_summary()
        badges = [
            ("Total Patients",   self.loader.count,              PALETTE["accent"]),
            ("Hypertension Risk", risk["hypertension_risk"],     PALETTE["danger"]),
            ("Fever Cases",      risk["fever_cases"],            PALETTE["accent3"]),
            ("Tachycardia",      risk["tachycardia_risk"],       PALETTE["accent3"]),
            ("Bradycardia",      risk["bradycardia_risk"],       PALETTE["accent2"]),
        ]
        for label, val, color in badges:
            badge = _StatBadge(self._dash_badges, label, val, color)
            badge.pack(side="left", padx=8)
            tk.Frame(badge, bg=color, height=3).pack(fill="x")

        lines = ["VITAL SIGNS RISK SUMMARY\n" + "="*40]
        lines.append(f"  Hypertension risk : {risk['hypertension_risk']} ({risk['hypertension_pct']}%)")
        lines.append(f"  Hypotension risk  : {risk['hypotension_risk']} ({risk['hypotension_pct']}%)")
        lines.append(f"  Tachycardia       : {risk['tachycardia_risk']} ({risk['tachycardia_pct']}%)")
        lines.append(f"  Bradycardia       : {risk['bradycardia_risk']} ({risk['bradycardia_pct']}%)")
        lines.append(f"  Fever (≥38°C)     : {risk['fever_cases']} ({risk['fever_pct']}%)")
        lines.append(f"  Hypothermia       : {risk['hypothermia_cases']} ({risk['hypothermia_pct']}%)")
        lines.append("\nTOP DIAGNOSES")
        lines.append("="*40)
        for diag, cnt in self.stats.top_diagnoses(10):
            bar = "█" * int(cnt / self.loader.count * 30)
            lines.append(f"  {diag:<25} {cnt:>4}  {bar}")
        lines.append("\nGENDER DISTRIBUTION")
        lines.append("="*40)
        for g, cnt in self.stats.gender_distribution().items():
            lines.append(f"  {g:<10} {cnt}")
        self._dash_write("\n".join(lines))

    def _dash_write(self, text: str):
        self._dash_text.config(state="normal")
        self._dash_text.delete("1.0", "end")
        self._dash_text.insert("end", text)
        self._dash_text.config(state="disabled")

    # ─── Patients table ──────────────────────────────────────────
    def _build_patients(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])

        hdr = tk.Frame(page, bg=PALETTE["bg"])
        hdr.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(hdr, text="Patient Records", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_HEAD).pack(side="left")

        # search bar
        self._pt_search_var = tk.StringVar()
        self._pt_search_var.trace_add("write", lambda *_: self._refresh_patient_table())
        tk.Entry(hdr, textvariable=self._pt_search_var,
                 bg=PALETTE["entry_bg"], fg=PALETTE["text"],
                 insertbackground=PALETTE["text"],
                 font=FONT_BODY, bd=0, width=30).pack(side="right", padx=4)
        tk.Label(hdr, text="🔍", bg=PALETTE["bg"],
                 fg=PALETTE["text_muted"]).pack(side="right")

        # treeview
        cols = ["ID","Name","Age","Gender","Blood","Diagnosis",
                "HR","BP Sys","BP Dia","Temp","Admitted","Status"]
        self._tree = ttk.Treeview(page, columns=cols, show="headings",
                                   selectmode="browse")
        self._style_tree()

        for c in cols:
            self._tree.heading(c, text=c, command=lambda col=c: self._sort_tree(col))
            self._tree.column(c, width=90, anchor="center")
        self._tree.column("Name", width=140, anchor="w")
        self._tree.column("Diagnosis", width=140, anchor="w")

        vsb = ttk.Scrollbar(page, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(fill="both", expand=True, padx=20, pady=4, side="left")
        vsb.pack(fill="y", side="right", pady=4, padx=(0, 20))

        # bottom actions
        act = tk.Frame(page, bg=PALETTE["bg"])
        act.pack(fill="x", padx=20, pady=8)
        for label, cmd, color in [
            ("View Details", self._view_patient, PALETTE["accent"]),
            ("Delete",       self._delete_patient, PALETTE["danger"]),
            ("Export CSV",   self._save_csv,       PALETTE["accent2"]),
        ]:
            tk.Button(act, text=label, bg=color, fg="#fff",
                      font=FONT_BODY, bd=0, padx=14, pady=6,
                      cursor="hand2", command=cmd).pack(side="left", padx=4)

        return page

    def _style_tree(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview",
                         background=PALETTE["card"],
                         foreground=PALETTE["text"],
                         fieldbackground=PALETTE["card"],
                         rowheight=26,
                         font=FONT_BODY)
        style.configure("Treeview.Heading",
                         background=PALETTE["header"],
                         foreground=PALETTE["text"],
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("Treeview",
                  background=[("selected", PALETTE["accent"])],
                  foreground=[("selected", "#fff")])

    def _refresh_patient_table(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        term = self._pt_search_var.get() if hasattr(self, "_pt_search_var") else ""
        if term:
            records = PatientQuery.search_all_fields(self.loader, term)
        else:
            records = self.loader.records
        for i, r in enumerate(records):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=r.patient_id, tags=(tag,),
                               values=(r.patient_id, r.name, r.age, r.gender,
                                       r.blood_group, r.diagnosis, r.heart_rate,
                                       r.blood_pressure_sys, r.blood_pressure_dia,
                                       r.temperature, r.admission_date, r.status))
        self._tree.tag_configure("even", background=PALETTE["row_even"])
        self._tree.tag_configure("odd",  background=PALETTE["row_odd"])
        self._update_status()

    _tree_sort_asc = True
    _tree_sort_col = "ID"

    def _sort_tree(self, col: str):
        field_map = {
            "ID":"patient_id","Name":"name","Age":"age","Gender":"gender",
            "Blood":"blood_group","Diagnosis":"diagnosis","HR":"heart_rate",
            "BP Sys":"blood_pressure_sys","BP Dia":"blood_pressure_dia",
            "Temp":"temperature","Admitted":"admission_date","Status":"status"
        }
        if self._tree_sort_col == col:
            self._tree_sort_asc = not self._tree_sort_asc
        else:
            self._tree_sort_asc = True
            self._tree_sort_col = col

        term = self._pt_search_var.get() if hasattr(self, "_pt_search_var") else ""
        records = (PatientQuery.search_all_fields(self.loader, term)
                   if term else self.loader.records)
        records = PatientQuery.sort_records(records, field_map[col], self._tree_sort_asc)

        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, r in enumerate(records):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=r.patient_id, tags=(tag,),
                               values=(r.patient_id, r.name, r.age, r.gender,
                                       r.blood_group, r.diagnosis, r.heart_rate,
                                       r.blood_pressure_sys, r.blood_pressure_dia,
                                       r.temperature, r.admission_date, r.status))
        self._tree.tag_configure("even", background=PALETTE["row_even"])
        self._tree.tag_configure("odd",  background=PALETTE["row_odd"])

    def _view_patient(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Select a patient", "Please click a row first.")
            return
        pid = sel[0]
        try:
            r = self.loader.get_record(pid)
        except KeyError as e:
            messagebox.showerror("Not found", str(e))
            return

        win = tk.Toplevel(self)
        win.title(f"Patient Details – {r.patient_id}")
        win.configure(bg=PALETTE["bg"])
        win.geometry("480x420")
        win.resizable(False, False)

        tk.Label(win, text=r.name, bg=PALETTE["bg"], fg=PALETTE["text"],
                 font=FONT_HEAD).pack(pady=(16, 4))
        tk.Label(win, text=f"ID: {r.patient_id}", bg=PALETTE["bg"],
                 fg=PALETTE["text_muted"], font=FONT_BODY).pack()

        info = tk.Frame(win, bg=PALETTE["card"], padx=20, pady=16)
        info.pack(fill="both", expand=True, padx=20, pady=16)

        fields = [
            ("Age", f"{r.age} yrs"),
            ("Gender", r.gender),
            ("Blood Group", r.blood_group),
            ("Diagnosis", r.diagnosis),
            ("Heart Rate", f"{r.heart_rate} bpm"),
            ("Blood Pressure", f"{r.blood_pressure_sys}/{r.blood_pressure_dia} mmHg"),
            ("Temperature", f"{r.temperature} °C"),
            ("Admission Date", r.admission_date),
            ("Status", r.status),
        ]
        for i, (lbl, val) in enumerate(fields):
            tk.Label(info, text=lbl+":", bg=PALETTE["card"],
                     fg=PALETTE["text_muted"], font=FONT_BODY,
                     width=16, anchor="e").grid(row=i, column=0, sticky="e", pady=3)
            tk.Label(info, text=val, bg=PALETTE["card"],
                     fg=PALETTE["text"], font=FONT_BODY,
                     anchor="w").grid(row=i, column=1, sticky="w", padx=10)

    def _delete_patient(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Select a patient", "Please click a row first.")
            return
        pid = sel[0]
        if messagebox.askyesno("Confirm Delete",
                                f"Delete patient '{pid}'? This cannot be undone."):
            try:
                self.loader.delete_record(pid)
                self._refresh_patient_table()
                messagebox.showinfo("Deleted", f"Patient {pid} deleted.")
            except KeyError as e:
                messagebox.showerror("Error", str(e))

    # ─── Query page ──────────────────────────────────────────────
    def _build_query(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])
        tk.Label(page, text="Query & Filter", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_HEAD).pack(anchor="w", padx=24, pady=(18, 6))

        form = _Card(page, title="Filter Parameters")
        form.pack(fill="x", padx=20, pady=4)

        self._q_vars: dict[str, tk.StringVar] = {}

        fields = [
            ("Name (contains)", "q_name"),
            ("Gender (Male/Female/Other)", "q_gender"),
            ("Blood Group", "q_blood"),
            ("Diagnosis (contains)", "q_diag"),
            ("Status (contains)", "q_status"),
            ("Age Min", "q_age_lo"),
            ("Age Max", "q_age_hi"),
            ("Heart Rate Min", "q_hr_lo"),
            ("Heart Rate Max", "q_hr_hi"),
            ("Admitted After (YYYY-MM-DD)", "q_date_after"),
            ("Admitted Before (YYYY-MM-DD)", "q_date_before"),
        ]
        inner = tk.Frame(form, bg=PALETTE["card"])
        inner.pack(fill="x", padx=12, pady=(0, 12))
        for i, (label, key) in enumerate(fields):
            col = i % 2
            row = i // 2
            var = tk.StringVar()
            self._q_vars[key] = var
            tk.Label(inner, text=label, bg=PALETTE["card"],
                     fg=PALETTE["text_muted"], font=FONT_BODY).grid(
                         row=row, column=col*2, sticky="w", padx=12, pady=4)
            tk.Entry(inner, textvariable=var,
                     bg=PALETTE["entry_bg"], fg=PALETTE["text"],
                     insertbackground=PALETTE["text"],
                     font=FONT_BODY, bd=0, width=22).grid(
                         row=row, column=col*2+1, sticky="w", padx=4, pady=4)

        btn_row = tk.Frame(form, bg=PALETTE["card"])
        btn_row.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(btn_row, text="Run Query", bg=PALETTE["accent"], fg="#fff",
                  font=FONT_BODY, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._run_query).pack(side="left", padx=4)
        tk.Button(btn_row, text="Critical Patients", bg=PALETTE["danger"], fg="#fff",
                  font=FONT_BODY, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._show_critical).pack(side="left", padx=4)
        tk.Button(btn_row, text="Clear", bg=PALETTE["card"], fg=PALETTE["text_muted"],
                  font=FONT_BODY, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._clear_query).pack(side="left", padx=4)

        self._q_result_label = tk.Label(page, text="", bg=PALETTE["bg"],
                                         fg=PALETTE["accent2"], font=FONT_BODY)
        self._q_result_label.pack(anchor="w", padx=24)

        self._q_tree_frame = tk.Frame(page, bg=PALETTE["bg"])
        self._q_tree_frame.pack(fill="both", expand=True, padx=20, pady=8)
        self._build_query_tree()

        return page

    def _build_query_tree(self):
        cols = ["ID","Name","Age","Gender","Diagnosis","HR","BP Sys","Temp","Status"]
        self._q_tree = ttk.Treeview(self._q_tree_frame, columns=cols,
                                     show="headings", selectmode="browse")
        for c in cols:
            self._q_tree.heading(c, text=c)
            self._q_tree.column(c, width=95, anchor="center")
        self._q_tree.column("Name", width=140, anchor="w")
        self._q_tree.column("Diagnosis", width=140, anchor="w")
        vsb = ttk.Scrollbar(self._q_tree_frame, orient="vertical",
                             command=self._q_tree.yview)
        self._q_tree.configure(yscrollcommand=vsb.set)
        self._q_tree.pack(fill="both", expand=True, side="left")
        vsb.pack(fill="y", side="right")

    def _run_query(self):
        if self.loader.count == 0:
            messagebox.showwarning("No data", "Load a dataset first.")
            return
        v = self._q_vars
        q = PatientQuery(self.loader)
        try:
            if v["q_name"].get():    q.by_name(v["q_name"].get())
            if v["q_gender"].get():  q.by_gender(v["q_gender"].get())
            if v["q_blood"].get():   q.by_blood_group(v["q_blood"].get())
            if v["q_diag"].get():    q.by_diagnosis(v["q_diag"].get())
            if v["q_status"].get():  q.by_status(v["q_status"].get())
            lo = v["q_age_lo"].get()
            hi = v["q_age_hi"].get()
            if lo or hi:
                q.age_between(int(lo or 0), int(hi or 130))
            lo_hr = v["q_hr_lo"].get()
            hi_hr = v["q_hr_hi"].get()
            if lo_hr or hi_hr:
                q.heart_rate_between(float(lo_hr or 0), float(hi_hr or 300))
            if v["q_date_after"].get():  q.admitted_after(v["q_date_after"].get())
            if v["q_date_before"].get(): q.admitted_before(v["q_date_before"].get())

            results = q.execute()
        except Exception as e:
            messagebox.showerror("Query Error", str(e))
            return

        self._populate_query_tree(results)
        self._q_result_label.config(
            text=f"✔  {len(results)} patient(s) matched")

    def _show_critical(self):
        if self.loader.count == 0:
            messagebox.showwarning("No data", "Load a dataset first.")
            return
        results = PatientQuery.critical_patients(self.loader)
        self._populate_query_tree(results)
        self._q_result_label.config(
            text=f"⚠  {len(results)} patient(s) with critical vital signs")

    def _clear_query(self):
        for var in self._q_vars.values():
            var.set("")
        for item in self._q_tree.get_children():
            self._q_tree.delete(item)
        self._q_result_label.config(text="")

    def _populate_query_tree(self, records):
        for item in self._q_tree.get_children():
            self._q_tree.delete(item)
        for i, r in enumerate(records):
            tag = "even" if i % 2 == 0 else "odd"
            self._q_tree.insert("", "end", tags=(tag,),
                                 values=(r.patient_id, r.name, r.age, r.gender,
                                         r.diagnosis, r.heart_rate,
                                         r.blood_pressure_sys, r.temperature, r.status))
        self._q_tree.tag_configure("even", background=PALETTE["row_even"])
        self._q_tree.tag_configure("odd",  background=PALETTE["row_odd"])

    # ─── Statistics page ─────────────────────────────────────────
    def _build_statistics(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])
        tk.Label(page, text="Descriptive Statistics", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_HEAD).pack(anchor="w", padx=24, pady=(18, 4))

        self._stats_text = tk.Text(page, bg=PALETTE["card"], fg=PALETTE["text"],
                                    font=FONT_MONO, relief="flat", bd=0,
                                    wrap="none", state="disabled")
        vsb = ttk.Scrollbar(page, orient="vertical", command=self._stats_text.yview)
        hsb = ttk.Scrollbar(page, orient="horizontal", command=self._stats_text.xview)
        self._stats_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        hsb.pack(fill="x", side="bottom", padx=20)
        vsb.pack(fill="y", side="right", pady=4, padx=(0, 20))
        self._stats_text.pack(fill="both", expand=True, padx=20, pady=4)
        return page

    def _refresh_statistics(self):
        if self.loader.count == 0:
            self._write_stats("No dataset loaded.")
            return
        lines = []
        for s in self.stats.all_fields_summary():
            lines.append(f"\n{'='*54}")
            lines.append(f"  Field : {s['field'].upper()}")
            lines.append(f"{'='*54}")
            for k, v in s.items():
                if k != "field":
                    lines.append(f"  {k:<12}: {v}")

        lines.append(f"\n{'='*54}")
        lines.append("  CORRELATION MATRIX")
        lines.append(f"{'='*54}")
        matrix = self.stats.correlation_matrix()
        fields = list(matrix.keys())
        header = f"{'':>12}" + "".join(f"{f[:8]:>10}" for f in fields)
        lines.append(header)
        for fa in fields:
            row = f"{fa[:12]:<12}" + "".join(f"{matrix[fa][fb]:>10.4f}" for fb in fields)
            lines.append(row)

        lines.append(f"\n{'='*54}")
        lines.append("  AVG VITALS BY DIAGNOSIS")
        lines.append(f"{'='*54}")
        lines.append(f"  {'Diagnosis':<25} {'N':>4} {'Age':>6} {'HR':>6} {'BPSys':>6} {'Temp':>6}")
        for diag, data in sorted(self.stats.avg_vitals_by_diagnosis().items()):
            lines.append(f"  {diag:<25} {data['count']:>4} {data['avg_age']:>6} "
                         f"{data['avg_hr']:>6} {data['avg_bp_sys']:>6} {data['avg_temp']:>6}")

        self._write_stats("\n".join(lines))

    def _write_stats(self, text: str):
        self._stats_text.config(state="normal")
        self._stats_text.delete("1.0", "end")
        self._stats_text.insert("end", text)
        self._stats_text.config(state="disabled")

    # ─── Charts page ─────────────────────────────────────────────
    def _build_charts(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])
        tk.Label(page, text="Charts & Visualisations", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_HEAD).pack(anchor="w", padx=24, pady=(18, 4))

        ctrl = tk.Frame(page, bg=PALETTE["bg"])
        ctrl.pack(fill="x", padx=20, pady=4)

        charts = [
            "Age Distribution (Histogram)",
            "Gender Distribution (Pie)",
            "Blood Group Distribution (Bar)",
            "Diagnosis Distribution (Bar)",
            "Status Distribution (Pie)",
            "Heart Rate Distribution (Histogram)",
            "BP Systolic Distribution (Histogram)",
            "Temperature Distribution (Histogram)",
            "Monthly Admissions (Line)",
            "Age Group Distribution (Bar)",
        ]
        self._chart_var = tk.StringVar(value=charts[0])
        tk.Label(ctrl, text="Select Chart:", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_BODY).pack(side="left")
        ttk.Combobox(ctrl, textvariable=self._chart_var, values=charts,
                     state="readonly", width=38).pack(side="left", padx=8)
        tk.Button(ctrl, text="Generate", bg=PALETTE["accent"], fg="#fff",
                  font=FONT_BODY, bd=0, padx=14, pady=6, cursor="hand2",
                  command=self._generate_chart).pack(side="left")

        self._chart_area = tk.Frame(page, bg=PALETTE["card"])
        self._chart_area.pack(fill="both", expand=True, padx=20, pady=8)

        if not MATPLOTLIB:
            tk.Label(self._chart_area,
                     text="matplotlib not installed.\nRun: pip install matplotlib",
                     bg=PALETTE["card"], fg=PALETTE["danger"],
                     font=FONT_BODY).pack(expand=True)

        return page

    def _generate_chart(self):
        if not MATPLOTLIB:
            return
        if self.loader.count == 0:
            messagebox.showwarning("No data", "Load a dataset first.")
            return
        choice = self._chart_var.get()

        for w in self._chart_area.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor(PALETTE["card"])
        ax.set_facecolor(PALETTE["bg"])
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])
        ax.tick_params(colors=PALETTE["text_muted"], labelsize=8)
        ax.title.set_color(PALETTE["text"])
        ax.xaxis.label.set_color(PALETTE["text_muted"])
        ax.yaxis.label.set_color(PALETTE["text_muted"])

        colors = [PALETTE["accent"], PALETTE["accent2"], PALETTE["accent3"],
                  PALETTE["danger"], "#8B5CF6", "#EC4899", "#14B8A6"]

        if "Age Distribution" in choice:
            vals = [r.age for r in self.loader.records]
            ax.hist(vals, bins=20, color=PALETTE["accent"], edgecolor=PALETTE["bg"])
            ax.set_title("Age Distribution"); ax.set_xlabel("Age"); ax.set_ylabel("Count")

        elif "Gender Distribution" in choice:
            d = self.stats.gender_distribution()
            ax.pie(d.values(), labels=d.keys(), autopct="%1.1f%%",
                   colors=colors[:len(d)], textprops={"color": PALETTE["text"]})
            ax.set_title("Gender Distribution")

        elif "Blood Group" in choice:
            d = self.stats.blood_group_distribution()
            ax.bar(d.keys(), d.values(), color=PALETTE["accent2"], edgecolor=PALETTE["bg"])
            ax.set_title("Blood Group Distribution"); ax.set_ylabel("Count")

        elif "Diagnosis Distribution" in choice:
            items = self.stats.top_diagnoses(10)
            labels, vals = zip(*items)
            ax.barh(labels, vals, color=PALETTE["accent3"])
            ax.invert_yaxis(); ax.set_title("Top 10 Diagnoses"); ax.set_xlabel("Count")

        elif "Status Distribution" in choice:
            d = self.stats.status_distribution()
            ax.pie(d.values(), labels=d.keys(), autopct="%1.1f%%",
                   colors=colors[:len(d)], textprops={"color": PALETTE["text"]})
            ax.set_title("Status Distribution")

        elif "Heart Rate" in choice:
            vals = [r.heart_rate for r in self.loader.records]
            ax.hist(vals, bins=20, color=PALETTE["danger"], edgecolor=PALETTE["bg"])
            ax.set_title("Heart Rate Distribution"); ax.set_xlabel("BPM"); ax.set_ylabel("Count")

        elif "BP Systolic" in choice:
            vals = [r.blood_pressure_sys for r in self.loader.records]
            ax.hist(vals, bins=20, color="#8B5CF6", edgecolor=PALETTE["bg"])
            ax.set_title("BP Systolic Distribution"); ax.set_xlabel("mmHg"); ax.set_ylabel("Count")

        elif "Temperature" in choice:
            vals = [r.temperature for r in self.loader.records]
            ax.hist(vals, bins=20, color=PALETTE["accent3"], edgecolor=PALETTE["bg"])
            ax.set_title("Temperature Distribution"); ax.set_xlabel("°C"); ax.set_ylabel("Count")

        elif "Monthly" in choice:
            d = self.stats.monthly_admissions()
            xs = list(d.keys()); ys = list(d.values())
            ax.plot(xs, ys, color=PALETTE["accent"], marker="o", linewidth=2)
            ax.fill_between(xs, ys, alpha=0.15, color=PALETTE["accent"])
            ax.set_title("Monthly Admissions"); ax.set_ylabel("Count")
            ax.set_xticks(range(len(xs))); ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=7)

        elif "Age Group" in choice:
            d = self.stats.age_group_distribution()
            ax.bar(d.keys(), d.values(), color=colors[:len(d)])
            ax.set_title("Age Group Distribution"); ax.set_ylabel("Count")
            plt.xticks(rotation=20, ha="right")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self._chart_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ─── Add patient page ────────────────────────────────────────
    def _build_add_patient(self) -> tk.Frame:
        page = tk.Frame(self._content, bg=PALETTE["bg"])
        tk.Label(page, text="Add New Patient", bg=PALETTE["bg"],
                 fg=PALETTE["text"], font=FONT_HEAD).pack(anchor="w", padx=24, pady=(18, 6))

        form = _Card(page)
        form.pack(fill="x", padx=20)

        fields = [
            ("Patient ID *",          "add_id"),
            ("Full Name *",           "add_name"),
            ("Age *",                 "add_age"),
            ("Gender * (Male/Female/Other)", "add_gender"),
            ("Blood Group * (A+/B-/…)", "add_blood"),
            ("Diagnosis *",           "add_diag"),
            ("Heart Rate (bpm) *",    "add_hr"),
            ("BP Systolic (mmHg) *",  "add_bp_sys"),
            ("BP Diastolic (mmHg) *", "add_bp_dia"),
            ("Temperature (°C) *",    "add_temp"),
            ("Admission Date * (YYYY-MM-DD)", "add_date"),
            ("Status *",              "add_status"),
        ]
        self._add_vars: dict[str, tk.StringVar] = {}
        inner = tk.Frame(form, bg=PALETTE["card"])
        inner.pack(fill="x", padx=16, pady=(0, 12))

        for i, (label, key) in enumerate(fields):
            col = i % 2
            row = i // 2
            var = tk.StringVar()
            self._add_vars[key] = var
            tk.Label(inner, text=label, bg=PALETTE["card"],
                     fg=PALETTE["text_muted"], font=FONT_BODY).grid(
                         row=row, column=col*2, sticky="w", padx=12, pady=4)
            tk.Entry(inner, textvariable=var,
                     bg=PALETTE["entry_bg"], fg=PALETTE["text"],
                     insertbackground=PALETTE["text"],
                     font=FONT_BODY, bd=0, width=24).grid(
                         row=row, column=col*2+1, sticky="w", padx=4, pady=4)

        self._add_msg = tk.Label(page, text="", bg=PALETTE["bg"],
                                  font=FONT_BODY)
        self._add_msg.pack(anchor="w", padx=24, pady=4)

        tk.Button(form, text="Add Patient", bg=PALETTE["accent2"], fg="#fff",
                  font=FONT_BODY, bd=0, padx=18, pady=8, cursor="hand2",
                  command=self._add_patient).pack(padx=16, pady=(0, 14), anchor="w")
        return page

    def _add_patient(self):
        v = self._add_vars
        try:
            record = PatientRecord(
                patient_id=v["add_id"].get(),
                name=v["add_name"].get(),
                age=v["add_age"].get(),
                gender=v["add_gender"].get(),
                blood_group=v["add_blood"].get(),
                diagnosis=v["add_diag"].get(),
                heart_rate=v["add_hr"].get(),
                blood_pressure_sys=v["add_bp_sys"].get(),
                blood_pressure_dia=v["add_bp_dia"].get(),
                temperature=v["add_temp"].get(),
                admission_date=v["add_date"].get(),
                status=v["add_status"].get(),
            )
            self.loader.add_record(record)
            for var in v.values():
                var.set("")
            self._add_msg.config(text=f"✔  Patient {record.patient_id} added successfully.",
                                  fg=PALETTE["accent2"])
            self._update_status()
        except (ValueError, KeyError) as e:
            self._add_msg.config(text=f"✘  {e}", fg=PALETTE["danger"])

    # ============================================================ #
    #   File operations                                            #
    # ============================================================ #
    def _load_csv(self):
        path = filedialog.askopenfilename(
            title="Open CSV", filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            loaded, errors = self.loader.load_csv(path)
            msg = f"Loaded {loaded} records from {os.path.basename(path)}."
            if errors:
                msg += f" ({len(errors)} error(s) — see console)"
                for e in errors[:10]:
                    print(e)
            messagebox.showinfo("Loaded", msg)
            self._update_status()
            self._show_page("dashboard")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _load_json(self):
        path = filedialog.askopenfilename(
            title="Open JSON", filetypes=[("JSON files", "*.json"), ("All", "*.*")])
        if not path:
            return
        try:
            loaded, errors = self.loader.load_json(path)
            messagebox.showinfo("Loaded", f"Loaded {loaded} records from {os.path.basename(path)}.")
            self._update_status()
            self._show_page("dashboard")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def _save_csv(self):
        if self.loader.count == 0:
            messagebox.showwarning("No data", "Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            try:
                self.loader.save_csv(path)
                messagebox.showinfo("Saved", f"Saved to {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _save_json(self):
        if self.loader.count == 0:
            messagebox.showwarning("No data", "Nothing to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            try:
                self.loader.save_json(path)
                messagebox.showinfo("Saved", f"Saved to {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _gen_sample(self):
        n = simpledialog.askinteger("Sample Data", "How many patients to generate?",
                                     initialvalue=100, minvalue=10, maxvalue=10000)
        if not n:
            return
        try:
            path = os.path.join(os.getcwd(), "sample_patients.csv")
            self.loader.generate_sample_data(n, path)
            messagebox.showinfo("Generated",
                                f"Generated {n} patients → {os.path.basename(path)}")
            self._update_status()
            self._show_page("dashboard")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================ #
    #   Status bar                                                 #
    # ============================================================ #
    def _update_status(self):
        if self.loader.count:
            fp = self.loader.filepath
            name = os.path.basename(fp) if fp else "unsaved"
            self._status_var.set(f"📋 {self.loader.count} patient(s) — {name}")
        else:
            self._status_var.set("No dataset loaded")
