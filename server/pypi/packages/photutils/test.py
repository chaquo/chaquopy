import unittest


class TestPhotutils(unittest.TestCase):

    # https://photutils.readthedocs.io/en/stable/getting_started.html
    def test_basic(self):
        from astropy.io import fits
        from astropy.stats import mad_std
        from io import BytesIO
        import numpy as np
        from photutils.aperture import aperture_photometry, CircularAperture
        from photutils.detection import DAOStarFinder

        # This is equivalent to photutils.datasets.load_star_image.
        URL = "http://www.astropy.org/astropy-data/photometry/M6707HH.fits"
        hdu = fits.open(BytesIO(read_url(URL)))[0]

        image = hdu.data[500:700, 500:700].astype(float)
        image -= np.median(image)

        bkg_sigma = mad_std(image)
        daofind = DAOStarFinder(fwhm=4.0, threshold=3.0 * bkg_sigma)
        sources = daofind(image)
        self.assertEqual(len(sources), 152)

        positions = np.transpose((sources['xcentroid'], sources['ycentroid']))
        apertures = CircularAperture(positions, r=4.0)
        phot_table = aperture_photometry(image, apertures)

        phot_table.sort("aperture_sum", reverse=True)
        brightest = phot_table[0]
        self.assertEqual(
            [int(brightest[column].value) for column in ["xcenter", "ycenter"]],
            [53, 13])  # See image at the bottom of the above link.


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
