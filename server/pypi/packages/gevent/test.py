import unittest


class TestGevent(unittest.TestCase):

    # From http://www.gevent.org/intro.html#example
    def test_gethostbyname(self):
        import gevent
        from gevent import socket
        import ipaddress

        jobs = []
        for addr in ['www.google.com', 'www.python.org']:
            job = gevent.spawn(socket.gethostbyname, addr)
            job.name = addr
            jobs.append(job)

        gevent.joinall(jobs, timeout=2)
        for job in jobs:
            with self.subTest(addr=job.name):
                self.assertTrue(job.dead)
                if job.exception:
                    raise job.exception
                ipaddress.ip_address(job.value)  # Raises ValueError for invalid address.
