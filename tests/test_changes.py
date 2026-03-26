import unittest
from autonomous_delivery import changes

class TestChanges(unittest.TestCase):
    def test_get_before_after(self):
        before, after = changes.get_before_after()
        self.assertIn("def foo()", before)
        self.assertIn("def foo()", after)

if __name__ == "__main__":
    unittest.main()
