import unittest


class TestSpacy(unittest.TestCase):
    maxDiff = None

    def test_basic(self):
        import spacy
        nlp = spacy.load("en_core_web_sm")
        result = nlp("This is Sparta").to_json()
        self.assertEqual(
            [{'id': 0, 'start': 0, 'end': 4, 'lemma': "this", 'morph': 'Number=Sing|PronType=Dem',
              'pos': 'PRON', 'tag': 'DT', 'dep': 'nsubj', 'head': 1},
             {'id': 1, 'start': 5, 'end': 7, 'lemma': 'be', 'morph': 'Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin',
              'pos': 'AUX', 'tag': 'VBZ', 'dep': 'ROOT', 'head': 1},
             {'id': 2, 'start': 8, 'end': 14, 'lemma': 'Sparta', 'morph': 'Number=Sing',
              'pos': 'PROPN', 'tag': 'NNP', 'dep': 'attr', 'head': 1}],
            result["tokens"])
