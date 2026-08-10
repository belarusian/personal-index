import unittest
from personal_index.content_health import check_health, get_health_report
class TestHealth(unittest.TestCase):
    def test_check(self): self.assertTrue(check_health("data"))
    def test_report(self): self.assertIsInstance(get_health_report("data"), dict)
if __name__=="__main__": unittest.main()
