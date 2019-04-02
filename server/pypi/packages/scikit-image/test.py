import unittest


class TestScikitImage(unittest.TestCase):

    # From https://scikit-image.org/docs/dev/user_guide/tutorial_segmentation.html
    def test_segmentation(self):
        import numpy as np
        from scipy import ndimage as ndi
        from skimage import data
        from skimage.filters import sobel
        from skimage.morphology import watershed

        coins = data.coins()
        elevation_map = sobel(coins)
        markers = np.zeros_like(coins)
        markers[coins < 30] = 1
        markers[coins > 150] = 2
        segmentation = watershed(elevation_map, markers)
        segmentation = ndi.binary_fill_holes(segmentation - 1)

        # The image only has 24 coins, but there's a false positive between the second and
        # third coins in the first row (visible in the bottom left image at the above link).
        self.assertEqual(25, ndi.label(segmentation)[1])
