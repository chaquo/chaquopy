import unittest


class TestDlib(unittest.TestCase):

    # From http://dlib.net/face_detector.py.html
    def test_face_detector(self):
        import dlib
        import pkgutil
        import tempfile

        with tempfile.NamedTemporaryFile(buffering=0) as f:
            f.write(pkgutil.get_data(__name__, "abba.jpg"))
            img = dlib.load_rgb_image(f.name)

        noses = [(95, 101), (202, 109), (306, 118), (393, 122)]
        for face in dlib.get_frontal_face_detector()(img, 1):
            self.assertLess(face.right() - face.left(), 100)
            self.assertLess(face.bottom() - face.top(), 100)
            for nose_x, nose_y in noses:
                if (face.left() < nose_x < face.right()) and \
                   (face.top() < nose_y < face.bottom()):
                    # It's safe to modify a list while iterating as long as we break
                    # immediately after.
                    noses.remove((nose_x, nose_y))
                    break
            else:
                self.fail("Unexpected face: {}".format(face))

        if noses:
            self.fail("Failed to find expected faces at {}".format(noses))
