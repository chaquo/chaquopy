import unittest


# The pyzmq recipe has a test for duplicate module basenames which depends on h5py. Add
# the word "Android" here so it'll show up during the pre-release package tests (see
# release/README.md).
class TestH5py(unittest.TestCase):

    def test_basic(self):
        import h5py
        import numpy
        import tempfile

        FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21]
        with tempfile.NamedTemporaryFile(suffix=".hdf5") as f:
            with h5py.File(f.name, "w") as hf:
                ds = hf.create_dataset("fibonacci", (8,), dtype=numpy.int32)
                ds[:] = FIBONACCI
            with h5py.File(f.name, "r") as hf:
                self.assertEqual(FIBONACCI, list(hf["fibonacci"]))
