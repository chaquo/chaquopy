import unittest


# Run TensorFlow test first to avoid suspected address space fragmentation problems on
# some 32-bit devices (#1209).
class Test01TensorFlow(unittest.TestCase):

    # Based on https://www.tensorflow.org/guide/keras/train_and_evaluate
    def test_mnist(self):
        import os
        from tensorflow import keras

        model = keras.Sequential([
            keras.Input((784,)),
            keras.layers.Dense(64, "relu"),
            keras.layers.Dense(64, "relu"),
            keras.layers.Dense(10)])
        model.compile(optimizer=keras.optimizers.RMSprop(),
                      loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                      metrics=["sparse_categorical_accuracy"])

        cache_url("https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz",
                  f"{os.environ['HOME']}/.keras/datasets")
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

    # With some combinations of TensorFlow and NumPy versions, this causes the error "Cannot
    # convert a symbolic Tensor ... to a numpy array" (#570).
    def test_lstm(self):
        from tensorflow import keras
        model = keras.Sequential()
        model.add(keras.layers.LSTM(85, input_shape=(1, 53)))


def cache_url(url, dir_name, base_name=None):
    import os

    if base_name is None:
        base_name = os.path.basename(url)
    filename = f"{dir_name}/{base_name}"
    if not os.path.exists(filename):
        os.makedirs(dir_name, exist_ok=True)
        data = read_url(url)
        with open(filename, "wb") as f:
            f.write(data)


# Downloading a URL with "Connection: close", as urllib does, causes an intermittent
# network problem on the emulator (https://issuetracker.google.com/issues/150758736). For
# small files we could just retry until it succeeds, but for large files a failure is much more
# likely, and we might have to keep retrying for several minutes. So use the stdlib's low-level
# HTTP API to make a request with no Connection header.
def read_url(url):
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse

    parsed = urlparse(url)
    conn_cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    conn = conn_cls(parsed.hostname, parsed.port)
    full_path = parsed.path
    if parsed.query:
        full_path += "?" + parsed.query
    conn.request("GET", full_path)
    data = conn.getresponse().read()
    conn.close()
    return data
