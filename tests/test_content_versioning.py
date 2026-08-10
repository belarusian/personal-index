import unittest
from personal_index.content_versioning import create_version, get_versions
class TestVersioning(unittest.TestCase):
    def test_create(self): self.assertIsNotNone(create_version("content", "v1"))
    def test_list(self): self.assertIsInstance(get_versions("content"), list)
if __name__=="__main__": unittest.main()
