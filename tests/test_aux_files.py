import unittest

from core.aux_files import (
    CATEGORY_ORDER,
    GENERIC_CONTINGENCY,
    AuxFileEntry,
    default_aux_selections,
    paths_for_case,
)


class AuxFileTests(unittest.TestCase):
    def test_defaults_include_every_category(self) -> None:
        defaults = default_aux_selections()
        self.assertEqual(tuple(defaults), CATEGORY_ORDER)
        self.assertTrue(defaults[GENERIC_CONTINGENCY])

    def test_case_specific_entry(self) -> None:
        selections = {
            GENERIC_CONTINGENCY: [
                {"path": "one.aux", "apply_to_all": False, "cases": ["case-a.pwb"]},
                {"path": "all.aux", "apply_to_all": True, "cases": []},
            ]
        }
        self.assertEqual(paths_for_case(selections, GENERIC_CONTINGENCY, "case-a.pwb"), ["one.aux", "all.aux"])
        self.assertEqual(paths_for_case(selections, GENERIC_CONTINGENCY, "case-b.pwb"), ["all.aux"])

    def test_blank_path_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AuxFileEntry(" ").validate()


if __name__ == "__main__":
    unittest.main()
