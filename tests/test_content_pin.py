import unittest
from personal_index.content_pin import pin_content, unpin_content
class TestPin(unittest.TestCase):
    def test_pin(self): self.assertTrue(pin_content("item_id"))
    def test_unpin(self): self.assertTrue(unpin_content("item_id"))
if __name__=="__main__": unittest.main()
