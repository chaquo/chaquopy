import unittest


class TestTensorFlow(unittest.TestCase):

    # Based on https://www.tensorflow.org/guide/keras
    def test_keras(self):
        NUM_SAMPLES = 500
        NUM_OUTPUTS = 5
        data_1, labels_1 = make_data(NUM_SAMPLES, NUM_OUTPUTS)
        data_2, labels_2 = make_data(NUM_SAMPLES, NUM_OUTPUTS)

        # There's a lot of variance in this test, so even with these thresholds there's a small
        # chance of it failing.
        self.assertGreater(self.get_accuracy(data_1, labels_1), 0.5)  # Matching data and labels
        self.assertLess(self.get_accuracy(data_1, labels_2), 0.5)  # Mismatching data and labels

    def get_accuracy(self, data, labels):
        model = make_model(data.shape[1])
        model.fit(data, labels, epochs=20, verbose=0)
        return model.evaluate(*make_data(*data.shape), verbose=0)[1]


def make_model(num_outputs):
    import tensorflow as tf
    from tensorflow.keras import layers

    model = tf.keras.Sequential([
        layers.Dense(num_outputs, activation='relu'),
        layers.Dense(64, activation='relu'),
        layers.Dense(num_outputs, activation='softmax')])
    model.compile(optimizer=tf.keras.optimizers.RMSprop(0.01),
                  loss=tf.keras.losses.categorical_crossentropy,
                  metrics=[tf.keras.metrics.categorical_accuracy])
    return model


def make_data(rows, cols):
    import numpy as np
    data = np.random.random((rows, cols))

    # Replace the highest value in each row with 1, and all other values with 0.
    labels = np.zeros((rows, cols))
    labels[np.arange(rows), np.argmax(data, 1)] = 1
    return data, labels
