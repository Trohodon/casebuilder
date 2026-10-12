import unittest

from core.distributed import (
    DistributedComputer,
    DistributedConfig,
    contingency_batch_bounds,
    render_distributed_aux,
    split_sequence,
)


class DistributedConfigTests(unittest.TestCase):
    def test_aux_contains_each_computer_once(self) -> None:
        config = DistributedConfig(
            100,
            (
                DistributedComputer("localhost", 4),
                DistributedComputer("S99589", 2),
            ),
        )
        text = render_distributed_aux(config)
        self.assertIn('"NO " "YES" "" 100', text)
        self.assertEqual(text.count('"localhost"'), 1)
        self.assertEqual(text.count('"S99589"'), 1)

    def test_invalid_connections_are_rejected(self) -> None:
        config = DistributedConfig(100, (DistributedComputer("server", 0),))
        with self.assertRaises(ValueError):
            render_distributed_aux(config)

    def test_batch_bounds_are_zero_based_and_complete(self) -> None:
        self.assertEqual(list(contingency_batch_bounds(7, 3)), [(0, 3), (3, 6), (6, 7)])
        values = [str(index) for index in range(7)]
        self.assertEqual(split_sequence(values, 3), [["0", "1", "2"], ["3", "4", "5"], ["6"]])


if __name__ == "__main__":
    unittest.main()
