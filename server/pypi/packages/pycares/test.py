import unittest


TIMEOUT = 1


class TestPycares(unittest.TestCase):

    def test_basic(self):
        import pycares
        from select import select
        import socket
        from time import time

        results = {}
        def callback(result, error):
            if error:  # This is NOT a Unix errno.
                self.fail(pycares.errno.strerror(error))
            results[result.name] = result.addresses

        channel = pycares.Channel()
        for name in ["google.com", "facebook.com"]:
            channel.gethostbyname(name, socket.AF_INET, callback)

        deadline = time() + TIMEOUT
        while True:
            now = time()
            if now > deadline:
                self.fail("Timeout")

            read_fds, write_fds = channel.getsock()
            if not (read_fds or write_fds):
                break
            rlist, wlist, xlist = select(read_fds, write_fds, [], deadline - now)
            for fd in rlist:
                channel.process_fd(fd, pycares.ARES_SOCKET_BAD)
            for fd in wlist:
                channel.process_fd(pycares.ARES_SOCKET_BAD, fd)

        self.assertEqual(["facebook.com", "google.com"], sorted(results.keys()))
        self.assertNotEqual(results["facebook.com"], results["google.com"])
