from os.path import dirname, join
import pkgutil
import unittest


class TestOpenCVContrib(unittest.TestCase):

    def test_haarcascade_jpg(self):
        self.check_haarcascade("jpg")

    def test_haarcascade_png(self):
        self.check_haarcascade("png")

    # Adapted from https://realpython.com/face-recognition-with-python/
    def check_haarcascade(self, ext):
        import cv2.data
        import numpy

        classifier = cv2.CascadeClassifier(cv2.data.haarcascades +
                                           "haarcascade_frontalface_default.xml")
        array = numpy.frombuffer(pkgutil.get_data(__name__, "abba." + ext), numpy.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
        faces = classifier.detectMultiScale(image, scaleFactor=1.1, minNeighbors=5,
                                            minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE)

        noses = [(95, 101), (202, 109), (306, 118), (393, 122)]
        for x, y, w, h in faces:
            self.assertLess(w, 100)
            self.assertLess(h, 100)
            for nose_x, nose_y in noses:
                if (x < nose_x < x + w) and (y < nose_y < y + h):
                    noses.remove((nose_x, nose_y))
                    break
            else:
                self.fail("Unexpected face: {}, {}, {}, {}".format(x, y, w, h))

        if noses:
            self.fail("Failed to find expected faces at {}".format(noses))

    def test_sift(self):
        import cv2.xfeatures2d

        img = cv2.imread(join(dirname(__file__), "triangle.png"))
        EXPECTED = [
            (216, 204, 6),      # Top-left corner
            (472, 114, 10),     # Top-right corner
            (765, 868, 12),     # Bottom corner
            (400, 250, 100),    # Apparently represents the triangle as a whole
        ]

        def close(expected, actual, margin):
            return abs(expected - actual) <= margin

        for point in cv2.xfeatures2d.SIFT_create().detect(img):
            for x_expected, y_expected, size_expected in EXPECTED:
                if close(x_expected, point.pt[0], 50) and \
                   close(y_expected, point.pt[1], 50) and \
                   close(size_expected, point.size, size_expected / 2):
                    break
            else:
                self.fail(f"Unexpected point: pt={point.pt}, size={point.size}")
