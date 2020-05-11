import unittest


class TestOpenCV(unittest.TestCase):

    def test_haarcascade_jpg(self):
        self.check_haarcascade("jpg")

    def test_haarcascade_png(self):
        self.check_haarcascade("png")

    # Adapted from https://realpython.com/face-recognition-with-python/
    def check_haarcascade(self, ext):
        import cv2.data
        import numpy
        import pkgutil

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
