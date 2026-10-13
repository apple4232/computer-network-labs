"""Additional reliability checks use varied bytes, unlike the supplied fixture."""
import random
import unittest
from unittest.mock import patch

from task1_rdt import Sender, Receiver, UnreliableChannel
import task2_measure


class ReliabilityTests(unittest.TestCase):
    def test_varied_data_and_channel_conditions(self):
        cases = 0
        for seed in range(30):
            for size in (0, 1, 7, 8, 9, 65, 2000):
                with self.subTest(seed=seed, size=size):
                    data = random.Random(seed).randbytes(size)
                    up = UnreliableChannel(seed, loss=0.3, dup=0.3, reorder=0.5)
                    down = UnreliableChannel(seed + 1000, loss=0.3, dup=0.3, reorder=0.5)
                    sender, receiver = Sender(up, down, data), Receiver(up, down)
                    for _ in range(200_000):
                        alive = sender.step()
                        receiver.step()
                        if not alive:
                            break
                    else:
                        self.fail('sender did not terminate')
                    self.assertEqual(receiver.data(), data)
                    cases += 1
        print(f'{cases} transfers: varied payloads, 30% loss, 30% duplicates, 50% reordering')


class MeasurementTests(unittest.TestCase):
    def test_error_pages_and_truncated_transfers_are_rejected(self):
        for output in ('0.01 0.02 0.03 0.1 5000000 403',
                       '0.01 0.02 0.03 0.1 100 200'):
            with self.subTest(output=output):
                with patch('task2_measure.subprocess.run') as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = output
                    with self.assertRaises(RuntimeError):
                        task2_measure.one_run()


if __name__ == '__main__':
    unittest.main()
