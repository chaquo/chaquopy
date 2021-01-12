from os.path import dirname
import unittest


class TestSentencePiece(unittest.TestCase):

    # Based on https://github.com/google/sentencepiece/blob/v0.1.95/python/README.md
    def test_basic(self):
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor(model_file=f"{dirname(__file__)}/test_model.model")
        self.assertEqual([284, 47, 11, 4, 15, 400],
                         sp.encode("This is a test"))
