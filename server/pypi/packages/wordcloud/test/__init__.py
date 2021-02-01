import unittest


class TestWordcloud(unittest.TestCase):

    # See https://github.com/amueller/word_cloud/blob/master/examples/simple.py
    def test_basic(self):
        from os.path import dirname, join
        from wordcloud import WordCloud

        with open(join(dirname(__file__), "constitution.txt")) as text_file:
            text = text_file.read()
        wordcloud = WordCloud(random_state=42).generate(text)
        a = wordcloud.to_array()
        self.assertEqual((200, 400, 3), a.shape)

        for x, y, color in [(144, 123, (72, 32, 113)),  # Purple ("State")
                            (265, 127, (72, 32, 113)),
                            (124, 60, (129, 211, 77)),  # Green ("Congress")
                            (218, 66, (129, 211, 77)),
                            (155, 63, (0, 0, 0)),       # Black (background)
                            (144, 137, (0, 0, 0))]:
            with self.subTest(x=x, y=y):
                self.assertEqual(color, tuple(a[y, x]))
