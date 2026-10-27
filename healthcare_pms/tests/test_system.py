import sys
import tempfile
import unittest
from pathlib import Path
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from database import (initialize,project_budget,revised_duration_weeks,get_activities,get_schedule,
                      approve_change,reject_change,dashboard_data)
from scheduling import calculate_schedule,parse_date
from evm import calculate_evm


class ProjectSystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"demo.sqlite3"
        self.conn=initialize(self.db)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_persistence_after_reopen(self):
        self.conn.execute("UPDATE project SET project_status='On Hold' WHERE id=1")
        self.conn.commit(); self.conn.close()
        self.conn=initialize(self.db)
        self.assertEqual(self.conn.execute("SELECT project_status FROM project WHERE id=1").fetchone()[0],"On Hold")

    def test_unapproved_requirement_and_wbs_stay_out_of_approved_scope(self):
        row=self.conn.execute("SELECT status FROM requirements WHERE code='REQ-07'").fetchone()
        wbs=self.conn.execute("SELECT status FROM wbs WHERE code='CR-001.1'").fetchone()
        self.assertEqual(row[0],"Pending");self.assertEqual(wbs[0],"Pending")
        self.assertEqual(project_budget(self.conn),5_000_000)
        self.assertEqual(len(get_activities(self.conn)),9)

    def test_approve_change_applies_combined_scope_budget_and_schedule_once(self):
        result=approve_change(self.conn,1)
        self.assertEqual(result,{"cost":800_000.0,"days":15,"weeks":3.0})
        self.assertEqual(project_budget(self.conn),5_800_000)
        self.assertEqual(revised_duration_weeks(self.conn),19)
        self.assertEqual(self.conn.execute("SELECT status FROM requirements WHERE code='REQ-07'").fetchone()[0],"Approved")
        self.assertEqual(self.conn.execute("SELECT status FROM wbs WHERE code='CR-001.1'").fetchone()[0],"Approved")
        self.assertEqual(len(get_activities(self.conn)),11)
        self.assertAlmostEqual(sum(a["budget"] for a in get_activities(self.conn)),5_800_000)
        with self.assertRaisesRegex(ValueError,"cannot be applied twice"):
            approve_change(self.conn,1)

    def test_rejection_keeps_original_baseline_and_excludes_scope(self):
        reject_change(self.conn,1)
        self.assertEqual(project_budget(self.conn),5_000_000)
        self.assertEqual(revised_duration_weeks(self.conn),16)
        self.assertEqual(self.conn.execute("SELECT status FROM requirements WHERE code='REQ-07'").fetchone()[0],"Rejected")
        self.assertEqual(self.conn.execute("SELECT status FROM wbs WHERE code='CR-001.1'").fetchone()[0],"Rejected")
        self.assertEqual(len(get_activities(self.conn)),9)

    def test_dependency_delay_moves_successor_but_not_independent_path(self):
        tasks=[{"id":1,"duration_days":2,"delay_days":3},{"id":2,"duration_days":2,"delay_days":0},{"id":3,"duration_days":5,"delay_days":0}]
        schedule=calculate_schedule(tasks,[(2,1)],"2026-01-05")
        self.assertEqual(schedule[1]["planned_finish"],date(2026,1,6))
        self.assertEqual(schedule[1]["forecast_finish"],date(2026,1,9))
        self.assertEqual(schedule[2]["planned_start"],date(2026,1,7))
        self.assertEqual(schedule[2]["forecast_start"],date(2026,1,12))
        self.assertEqual(schedule[3]["forecast_finish"],date(2026,1,9))

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):parse_date("2026-02-30")
        with self.assertRaises(ValueError):calculate_schedule([],[],"not-a-date")

    def test_self_and_circular_dependencies_rejected(self):
        tasks=[{"id":1,"duration_days":1},{"id":2,"duration_days":1}]
        with self.assertRaisesRegex(ValueError,"cannot depend on itself"):
            calculate_schedule(tasks,[(1,1)],"2026-01-05")
        with self.assertRaisesRegex(ValueError,"Circular dependency"):
            calculate_schedule(tasks,[(1,2),(2,1)],"2026-01-05")

    def test_evm_matches_manual_task_level_example(self):
        tasks=[{"id":1,"duration_days":2,"budget":1000,"actual_progress":40},{"id":2,"duration_days":1,"budget":500,"actual_progress":0}]
        schedule=calculate_schedule(tasks,[(2,1)],"2026-01-05",delays=False)
        actual=[{"activity_id":1,"amount":450,"spent_on":"2026-01-05"}]
        result=calculate_evm(tasks,actual,schedule,"2026-01-05")
        self.assertAlmostEqual(result["pv"],500)
        self.assertAlmostEqual(result["ev"],400)
        self.assertAlmostEqual(result["ac"],450)
        self.assertAlmostEqual(result["cpi"],400/450)
        self.assertAlmostEqual(result["spi"],0.8)

    def test_zero_denominators_return_na_values(self):
        tasks=[{"id":1,"duration_days":1,"budget":100,"actual_progress":0}]
        schedule=calculate_schedule(tasks,[],"2026-01-05")
        result=calculate_evm(tasks,[],schedule,"2026-01-04")
        self.assertEqual(result["pv"],0);self.assertIsNone(result["spi"]);self.assertIsNone(result["cpi"])

    def test_negative_cost_and_invalid_progress_rejected(self):
        schedule={1:{"planned_start":date(2026,1,5),"planned_finish":date(2026,1,5)}}
        with self.assertRaisesRegex(ValueError,"cannot be negative"):
            calculate_evm([{"id":1,"duration_days":1,"budget":-1,"actual_progress":0}],[],schedule,"2026-01-05")
        with self.assertRaisesRegex(ValueError,"between 0 and 100"):
            calculate_evm([{"id":1,"duration_days":1,"budget":10,"actual_progress":101}],[],schedule,"2026-01-05")
        with self.assertRaisesRegex(ValueError,"cannot be negative"):
            calculate_evm([{"id":1,"duration_days":1,"budget":10,"actual_progress":0}],[{"activity_id":1,"amount":-1,"spent_on":"2026-01-05"}],schedule,"2026-01-05")

    def test_critical_defects_and_risk_ranking_are_persisted(self):
        critical=self.conn.execute("SELECT COUNT(*) FROM defects WHERE severity='Critical' AND status<>'Resolved'").fetchone()[0]
        risks=list(self.conn.execute("SELECT code,likelihood*impact score FROM risks ORDER BY score DESC,id"))
        self.assertEqual(critical,2)
        self.assertEqual(risks[0]["score"],20)
        self.assertEqual(risks[-1]["score"],12)

    def test_dashboard_reconciles_after_approval(self):
        before=dashboard_data(self.conn)
        approve_change(self.conn,1)
        after=dashboard_data(self.conn)
        self.assertEqual(before["approved_budget"],5_000_000)
        self.assertEqual(after["approved_budget"],5_800_000)
        self.assertEqual(before["pending_changes"],1)
        self.assertEqual(after["pending_changes"],0)
        self.assertEqual(after["unresolved_critical_defects"],2)
        self.assertEqual(len(after["schedule"]),11)

    def test_sample_evm_status_date(self):
        metrics=calculate_evm(get_activities(self.conn),[dict(r) for r in self.conn.execute("SELECT * FROM expenditures")],get_schedule(self.conn),"2026-02-10")
        self.assertAlmostEqual(metrics["pv"],2_053_333.333333,places=2)
        self.assertAlmostEqual(metrics["ev"],2_140_000)
        self.assertAlmostEqual(metrics["ac"],2_205_000)


if __name__=="__main__":
    unittest.main(verbosity=2)
