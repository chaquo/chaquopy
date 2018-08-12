from __future__ import absolute_import, division, print_function

import sys
import unittest


class TestSpacy(unittest.TestCase):

    maxDiff = None

    # Based on https://spacy.io/usage/models#usage
    def test_basic(self):
        import spacy
        nlp = spacy.load("en_core_web_sm")
        tree = nlp(u"This is Sparta").print_tree()
        self.assertEqual(
            [{'NE': '',
              'POS_coarse': 'VERB',
              'POS_fine': 'VBZ',
              'arc': 'ROOT',
              'lemma': 'be',
              'modifiers': [{'NE': '',
                             'POS_coarse': 'DET',
                             'POS_fine': 'DT',
                             'arc': 'nsubj',
                             'lemma': 'this',
                             'modifiers': [],
                             'word': 'This'},
                            {'NE': 'GPE',
                             'POS_coarse': 'PROPN',
                             'POS_fine': 'NNP',
                             'arc': 'attr',
                             # No idea why this happens, but it's the same on Linux.
                             'lemma': 'sparta' if sys.version_info[:2] < (3, 6) else 'Sparta',
                             'modifiers': [],
                             'word': 'Sparta'}],
              'word': 'is'}],
            tree)
