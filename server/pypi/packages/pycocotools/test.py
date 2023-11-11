import unittest

class TestPycocotools(unittest.TestCase):

    def test_mask(self):
        from pycocotools import mask
        import numpy as np

        #Define a binary mask as a 2D list
        binary_mask = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8, order='F')

        #Encode the binary mask
        rle_encoded = mask.encode(binary_mask)

        #Decode the RLE-encoded mask
        decoded_mask = mask.decode(rle_encoded)

        #Check if the decoded mask matches the original binary mask
        self.assertTrue(np.array_equal(decoded_mask, binary_mask))
