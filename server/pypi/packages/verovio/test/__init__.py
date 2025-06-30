from os.path import dirname, join
import unittest

class TestVerovio(unittest.TestCase):

    def test_basic(self):
        import verovio

        tk = verovio.toolkit()
        tk.loadFile(join(dirname(__file__), "Schubert_Lindenbaum.mei"))

        print(tk.getPageCount())
        #self.assertEqual(tk.getPageCount(), <number here>)

        svg_string: str = tk.renderToSVG(1)
        print(svg_string)
        #self.assertEqual(svg_string, <string here>)
