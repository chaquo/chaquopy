import unittest


class TestWordcloud(unittest.TestCase):

    # https://github.com/amueller/word_cloud/blob/master/examples/simple.py
    def test_basic(self):
        from os.path import dirname, join
        import numpy as np
        from wordcloud import WordCloud

        with open(join(dirname(__file__), "constitution.txt")) as text_file:
            text = text_file.read()
        wordcloud = WordCloud(random_state=42).generate(text)

        HEIGHT = 200
        WIDTH = 400
        a = wordcloud.to_array()
        self.assertEqual(a.shape, (HEIGHT, WIDTH, 3))
        self.assertEqual(a.dtype, np.uint8)

        # Output is not perfectly reproducible, even with a fixed random_state. And even
        # wordcloud's own unit tests don't appear to cover the layout algorithm. So just
        # make sure that the middle row of the image contains at least one black pixel
        # and one reasonably-light pixel.
        found_black = found_light = False
        for x in range(WIDTH):
            color = a[HEIGHT // 2, x]
            if tuple(color) == (0, 0, 0):
                found_black = True
            elif max(color) > 100:
                found_light = True

        self.assertTrue(found_black)
        self.assertTrue(found_light)
