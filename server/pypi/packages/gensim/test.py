import unittest

class TestGensim(unittest.TestCase):

    # Based on https://radimrehurek.com/gensim_3.8.3/auto_examples/tutorials/run_doc2vec_lee.html
    def test_doc2vec(self):
        import gensim
        import gensim.test.utils

        with open(gensim.test.utils.datapath("lee_background.cor")) as data_file:
            corpus = [
                gensim.models.doc2vec.TaggedDocument(
                    gensim.utils.simple_preprocess(line),
                    [i])
                for i, line in enumerate(data_file)]

        for i, words in [(299, "australia will take on france"),
                         (104, "australian cricket captain steve waugh"),
                         (243, "four afghan factions have reached")]:
            self.assertEqual(words.split(), corpus[i].words[:5])

        model = gensim.models.doc2vec.Doc2Vec(vector_size=50, min_count=2, epochs=40)
        model.build_vocab(corpus)
        model.train(corpus, total_examples=model.corpus_count, epochs=model.epochs)
        dv = model.docvecs

        self.assertGreater(dv.similarity(299, 104), 0.8)
        self.assertLess(dv.similarity(299, 243), 0.2)
        self.assertLess(dv.similarity(104, 243), 0.2)
