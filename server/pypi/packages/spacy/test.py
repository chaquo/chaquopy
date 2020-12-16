import unittest


class TestSpacy(unittest.TestCase):
    maxDiff = None

    def test_basic(self):
        import spacy
        nlp = spacy.load("en_core_web_sm")
        result = nlp("This is Sparta").to_json()
        self.assertEqual(
            [{'id': 0, 'start': 0, 'end': 4, 'pos': 'DET', 'tag': 'DT', 'dep': 'nsubj', 'head': 1},
             {'id': 1, 'start': 5, 'end': 7, 'pos': 'AUX', 'tag': 'VBZ', 'dep': 'ROOT', 'head': 1},
             {'id': 2, 'start': 8, 'end': 14, 'pos': 'PROPN', 'tag': 'NNP', 'dep': 'attr',
              'head': 1}],
            result["tokens"])
