from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.powerworld import PowerWorldClient, PowerWorldError, powerworld_executable_candidates
from core.preparation import default_prepared_case_path, prepare_case


class FakeAutomation:
    def __init__(self, fail_aux: bool = False) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.fail_aux = fail_aux

    def OpenCase(self, path: str):
        self.calls.append(("open", path))
        return ("",)

    def ProcessAuxFile(self, path: str):
        self.calls.append(("aux", path))
        return ("bad aux") if self.fail_aux else ("",)

    def RunScriptCommand(self, command: str):
        self.calls.append(("script", command))
        return ("",)

    def SaveCase(self, path: str, file_type: str, overwrite: bool):
        self.calls.append(("save", path, file_type, overwrite))
        return ("",)

    def CloseCase(self):
        self.calls.append(("close",))
        return ("",)

    def ChangeParametersSingleElement(self, object_type, fields, values):
        self.calls.append(("change", object_type, fields, values))
        return ("",)

    def GetParametersMultipleElement(self, object_type, fields, filter_name):
        self.calls.append(("get", object_type, fields, filter_name))
        return ("", [["CTG1"], ["Branch 1"], ["Limit"], ["101"], ["100"], ["101"], ["100"], ["YES"]])

    def WriteAuxFile(self, path, filter_name, object_type, append, fields):
        self.calls.append(("write_aux", path, filter_name, object_type, append, fields))
        return ("",)


class PowerWorldClientTests(unittest.TestCase):
    def test_executable_candidates_cover_legacy_install_names(self) -> None:
        candidates = [str(path) for path in powerworld_executable_candidates(24)]
        self.assertTrue(any("Simulator24" in path for path in candidates))
        self.assertTrue(any("Simulator 24" in path for path in candidates))
        self.assertTrue(any("Program Files (x86)" in path for path in candidates))

    def test_prepare_case_applies_aux_and_con_in_order(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = root / "case.pwb"
            aux = root / "settings.aux"
            con = root / "external.con"
            output = root / "prepared.pwb"
            for path in (case, aux, con):
                path.touch()
            automation = FakeAutomation()

            result = prepare_case(PowerWorldClient(automation), case, output, (aux, con))

            self.assertEqual(output, result)
            self.assertEqual("open", automation.calls[0][0])
            self.assertEqual("aux", automation.calls[1][0])
            self.assertEqual("script", automation.calls[2][0])
            self.assertIn("CTGReadFilePTI", str(automation.calls[2][1]))
            self.assertEqual("save", automation.calls[3][0])
            self.assertTrue(automation.calls[3][3])
            self.assertEqual(("close",), automation.calls[4])

    def test_prepare_case_closes_after_powerworld_error(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = root / "case.pwb"
            aux = root / "bad.aux"
            case.touch()
            aux.touch()
            automation = FakeAutomation(fail_aux=True)

            with self.assertRaises(PowerWorldError):
                prepare_case(PowerWorldClient(automation), case, root / "out.pwb", (aux,))

            self.assertEqual(("close",), automation.calls[-1])

    def test_default_prepared_case_name(self) -> None:
        result = default_prepared_case_path(Path("study.raw"), "_withAUXapplied")
        self.assertEqual(Path("study_withAUXapplied.PWB"), result)


if __name__ == "__main__":
    unittest.main()
