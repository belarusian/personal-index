import unittest
from personal_index.content_rollback import rollback_to, can_rollback
class TestRollback(unittest.TestCase):
    def test_can(self): self.assertTrue(can_rollback("content", "v1"))
    def test_rollback(self): self.assertTrue(rollback_to("content", "v1"))
if __name__=="__main__": unittest.main()
