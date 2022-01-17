import unittest


class TestTokenizers(unittest.TestCase):

    # See https://huggingface.co/docs/tokenizers/python/latest/quicktour.html
    def test_basic(self):
        from os.path import dirname
        from tokenizers import Tokenizer
        from tokenizers.models import BPE
        from tokenizers.pre_tokenizers import Whitespace
        from tokenizers.trainers import BpeTrainer

        for size, vocab, tokens in [
            (0, "? a c d f h i k l m o u w", "c h i c k"),
            (20, "? a c ch chuck ck d f h i k l m o od u uck w wo wood", "ch i ck"),
        ]:
            with self.subTest(size=size):
                tokenizer = Tokenizer(BPE())
                tokenizer.pre_tokenizer = Whitespace()
                trainer = BpeTrainer(vocab_size=size)
                tokenizer.train([f"{dirname(__file__)}/train.txt"], trainer)
                self.assertEqual(vocab.split(), sorted(tokenizer.get_vocab()))
                self.assertEqual(tokens.split(), tokenizer.encode("chick").tokens)
