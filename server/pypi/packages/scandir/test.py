import unittest


class TestScandir(unittest.TestCase):

    def test_basic(self):
        import os
        from tempfile import mkdtemp

        from scandir import scandir

        temp_dir = mkdtemp()
        temp_filename = os.path.join(temp_dir, "temp.txt")
        with open(temp_filename, "w"):
            pass
        scan = list(scandir(temp_dir))
        self.assertEqual(1, len(scan))
        self.assertEqual("temp.txt", scan[0].name)
        os.remove(temp_filename)
        os.rmdir(temp_dir)
