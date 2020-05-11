import unittest


class TestNetifaces(unittest.TestCase):

    def test_basic(self):
        import netifaces
        TEST_ADDRESS = "127.0.0.1"
        for iface_name in netifaces.interfaces():
            iface_info = netifaces.ifaddresses(iface_name)
            try:
                addrs = iface_info[netifaces.AF_INET]
            except KeyError:
                continue
            for addr_info in addrs:
                if addr_info["addr"] == TEST_ADDRESS:
                    return
        self.fail("Failed to find address " + TEST_ADDRESS)
