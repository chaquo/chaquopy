import unittest


class TestTensorFlow(unittest.TestCase):

    # Based on https://www.tensorflow.org/guide/keras/train_and_evaluate
    def test_mnist(self):
        from tensorflow import keras

        model = keras.Sequential([
            keras.Input((784,)),
            keras.layers.Dense(64, "relu"),
            keras.layers.Dense(64, "relu"),
            keras.layers.Dense(10)])
        model.compile(optimizer=keras.optimizers.RMSprop(),
                      loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                      metrics=["sparse_categorical_accuracy"])

        (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
        x_train = x_train.reshape(60000, 784).astype("float32") / 255
        x_test = x_test.reshape(10000, 784).astype("float32") / 255
        y_train = y_train.astype("float32")
        y_test = y_test.astype("float32")

        history = model.fit(x_train, y_train, validation_split=0.15, verbose=0)
        self.assertGreater(history.history["val_sparse_categorical_accuracy"][-1], 0.9)

        # To see these images:
        #   >>> (x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()
        #   >>> np.set_printoptions(linewidth=150)
        #   >>> x_test[0] etc.
        self.assertEqual([7, 2, 1, 0, 4],
                         model.predict(x_test[:5]).argmax(axis=1).tolist())
