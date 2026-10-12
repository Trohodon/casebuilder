from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.analysis import AnalysisOptions, ContingencyOptions, ContingencyWorkflow
from core.powerworld import PowerWorldClient
from core.settings import AppSettings
from tests.test_powerworld import FakeAutomation


RESOURCE_NAMES = (
    "Basecase.aux",
    "P1_All_Except_CB-CB.aux",
    "N-2_Branches&TFMRs.aux",
    "P2_All_Except_BF.aux",
    "UG_Lines.aux",
    "EE_DBL_Branch.aux",
    "EE_DBL_Bus.aux",
    "Conts_Filters.aux",
)


class AnalysisWorkflowTests(unittest.TestCase):
    def _fixture(self, root: Path):
        case = root / "study.pwb"
        case.touch()
        resources = root / "Resources"
        resources.mkdir()
        for name in RESOURCE_NAMES:
            (resources / name).touch()
        automation = FakeAutomation()
        settings = AppSettings(use_distributed=False)
        workflow = ContingencyWorkflow(
            PowerWorldClient(automation), settings, resources_dir=resources
        )
        return case, automation, workflow

    def test_default_join_active_analysis_command_order(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case, automation, workflow = self._fixture(root)
            contingencies = ContingencyOptions(
                n1=True, n11=True, long_term_p2=True
            )
            analysis = AnalysisOptions(
                create_pwb=True,
                create_aux=False,
                create_csv=False,
                use_distributed=False,
            )

            result = workflow.run_analysis(case, root / "output", contingencies, analysis)

            scripts = [str(call[1]) for call in automation.calls if call[0] == "script"]
            self.assertIn("SolvePowerFlow;", scripts)
            self.assertIn('CTGSolve("BASECASE");', scripts)
            self.assertIn("CTGJoinActiveCTGs(NO,NO,YES);", scripts)
            self.assertIn("CTGSolveAll(NO);", scripts)
            self.assertIn('Delete(Contingency, "SKIPPED");', scripts)
            self.assertEqual(
                (
                    root / "output" / "study_DCwACver_P1,2,4,7.PWB",
                    root / "output" / "study_DCwACver_P1-7.PWB",
                    root / "output" / "study_DCwACver_LongTerm.PWB",
                ),
                result.outputs,
            )
            self.assertEqual(("close",), automation.calls[-1])

    def test_csv_output_is_written_without_excel(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case, _automation, workflow = self._fixture(root)
            result = workflow.run_analysis(
                case,
                root,
                ContingencyOptions(n1=True, n11=False, long_term_p2=False),
                AnalysisOptions(
                    create_pwb=False,
                    create_aux=False,
                    create_csv=True,
                    use_distributed=False,
                ),
            )

            csv_path = root / "study_DCwACver_P1,2,4,7.CSV"
            self.assertEqual((csv_path,), result.outputs)
            contents = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("CTGLabel", contents)
            self.assertIn("CTG1", contents)

    def test_pti_writer_uses_requested_truncation_and_closes(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case, automation, workflow = self._fixture(root)
            output = root / "study.con"

            workflow.write_pti_contingencies(
                case,
                output,
                ContingencyOptions(n1=True, n11=False, long_term_p2=False),
                truncate_labels=True,
            )

            scripts = [str(call[1]) for call in automation.calls if call[0] == "script"]
            self.assertTrue(any("CTGWriteFilePTI" in command and '"YES"' in command for command in scripts))
            self.assertEqual(("close",), automation.calls[-1])

    def test_analysis_rejects_no_outputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "output"):
            AnalysisOptions(create_pwb=False, create_aux=False, create_csv=False).validate()

    def test_preflight_reports_missing_files_before_opening_case(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case, automation, workflow = self._fixture(root)
            (root / "Resources" / "P1_All_Except_CB-CB.aux").unlink()

            with self.assertRaisesRegex(Exception, "P1_All_Except"):
                workflow.run_analysis(
                    case,
                    root,
                    ContingencyOptions(n1=True, n11=False, long_term_p2=False),
                    AnalysisOptions(use_distributed=False),
                )

            self.assertEqual([], automation.calls)

    def test_full_ac_uses_complete_non_overlapping_batches(self) -> None:
        class BatchAutomation(FakeAutomation):
            def GetParametersMultipleElement(self, object_type, fields, filter_name):
                self.calls.append(("get", object_type, fields, filter_name))
                return ("", [["A", "B", "C", "D", "E"], ["NO"] * 5, [""] * 5, [""] * 5])

        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = root / "study.pwb"
            case.touch()
            resources = root / "Resources"
            resources.mkdir()
            for name in RESOURCE_NAMES:
                (resources / name).touch()
            automation = BatchAutomation()
            workflow = ContingencyWorkflow(
                PowerWorldClient(automation),
                AppSettings(use_distributed=False),
                resources_dir=resources,
            )

            workflow.run_analysis(
                case,
                root,
                ContingencyOptions(n1=True, n11=False, long_term_p2=False),
                AnalysisOptions(
                    full_ac=True,
                    contingencies_per_file=2,
                    use_distributed=False,
                ),
            )

            solve_calls = [call for call in automation.calls if call == ("script", "CTGSolveAll(NO);")]
            self.assertEqual(3, len(solve_calls))


if __name__ == "__main__":
    unittest.main()
