from contextlib import nullcontext
import unittest
import warnings


class TestCvxopt(unittest.TestCase):

    # See https://cvxopt.org/userguide/spsolvers.html#cvxopt.cholmod.linsolve
    #
    # This test gives incorrect output on x86 in the "supernodal" mode which is enabled by
    # default. All other ABIs work fine, and so does the PyPI Windows x86 build.
    #
    # According to
    # https://github.com/DrTimothyAldenDavis/SuiteSparse/issues/1#issuecomment-545458627, this
    # may be a problem with OpenBLAS, which is why the SuiteSparse README "strongly recommends"
    # not using OpenBLAS. However, we don't currently have any alternative available.
    #
    # None of the following things made any difference:
    #
    #  * Running the x86 build on an x86_64 emulator
    #  * Upgrading OpenBLAS to the current stable version 0.3.10 (the PyPI Linux builds
    #    currently use 0.2.19, very close to our own 0.2.20).
    #  * Trying other versions of cvxopt / SuiteSparse:
    #     * 1.2.4 / 5.6.0
    #     * 1.2.0 / 5.2.0
    #     * 1.1.9 / 4.5.3
    #  * Removing the libm.a workaround and building against API level 26.
    #  * Building x86 using DLONG, and altering cholmod.c etc. accordingly.
    #
    # I've patched the x86 build to disable supernodal mode by default on that ABI, but this
    # still doesn't fix the test below, so I've added a warning as well.
    def test_cholmod(self):
        try:
            from android.os import Build
            ANDROID_ABI = Build.CPU_ABI
        except ImportError:
            ANDROID_ABI = None

        with warnings.catch_warnings():
            warnings.filterwarnings("error")  # Other ABIs should have no warning.
            with (nullcontext() if ANDROID_ABI != "x86" else
                  self.assertWarnsRegex(UserWarning,
                                        "This cvxopt build is unreliable on x86: see "
                                        "https://github.com/chaquo/chaquopy/issues/388")):
                from cvxopt import matrix, spmatrix, cholmod

        A = spmatrix([10, 3, 5, -2, 5, 2], [0, 2, 1, 3, 2, 3], [0, 0, 1, 1, 2, 3])
        X = matrix(range(8), (4, 2), 'd')
        cholmod.linsolve(A, X)
        self.assertEqual("[-1.46e-01  4.88e-02]\n"
                         "[ 1.33e+00  4.00e+00]\n"
                         "[ 4.88e-01  1.17e+00]\n"
                         "[ 2.83e+00  7.50e+00]\n",
                         str(X))

        if ANDROID_ABI == "x86":
            # Test the incorrect output so we'll find out if this is ever fixed.
            prev_supernodal = cholmod.options.pop("supernodal")
            X = matrix(range(8), (4, 2), 'd')
            cholmod.linsolve(A, X)
            self.assertEqual("[-3.75e-01  4.38e-01]\n"
                             "[ 6.88e-01  2.44e+00]\n"
                             "[ 5.00e-01  7.50e-01]\n"
                             "[ 8.75e-01  2.38e+00]\n",
                             str(X))
            cholmod.options["supernodal"] = prev_supernodal

    # See https://github.com/neuropsychology/NeuroKit/blob/master/tests/tests_eda.py.
    #
    # This test originally failed on x86 with the following exception:
    #
    #    Traceback (most recent call last):
    #      File ".../cvxopt/misc.py", line 1432, in factor
    #    ArithmeticError: 1
    #
    #    During handling of the above exception, another exception occurred:
    #
    #    Traceback (most recent call last):
    #      File ".../cvxopt/coneprog.py", line 2065, in coneqp
    #      File ".../cvxopt/coneprog.py", line 1981, in kktsolver
    #      File ".../cvxopt/misc.py", line 1447, in factor
    #    ArithmeticError: 1
    #
    #    During handling of the above exception, another exception occurred:
    #
    #    Traceback (most recent call last):
    #      File ".../chaquopy/test/cvxopt.py", line 13, in test_eda_phasic
    #        cvxEDA = nk.eda_phasic(nk.standardize(eda), method="cvxeda")
    #      File ".../neurokit2/eda/eda_phasic.py", line 72, in eda_phasic
    #      File ".../neurokit2/eda/eda_phasic.py", line 240, in _eda_phasic_cvxeda
    #      File ".../cvxopt/coneprog.py", line 4485, in qp
    #      File ".../cvxopt/coneprog.py", line 2067, in coneqp
    #    ValueError: Rank(A) < p or Rank([P; A; G]) < n
    #
    # Disabling supernodal mode allows it to run without crashing, but it still gives incorrect
    # output:
    #
    #            EDA_Tonic    EDA_Phasic
    #    0     -585.911110  0.000000e+00
    #    1     -585.897707  0.000000e+00
    #    2     -585.884294 -5.622325e+03
    #    3     -585.870873 -4.004758e+05
    #    4     -585.857442 -1.043021e+06
    #    ...           ...           ...
    #    29995  305.384372  2.877671e+11
    #    29996  305.402341  2.872935e+11
    #    29997  305.420310  2.868207e+11
    #    29998  305.438278  2.863485e+11
    #    29999  305.456247  2.858770e+11
    #
    # All other ABIs, and the PyPI Windows x86 build, give something like this:
    #
    #           EDA_Tonic  EDA_Phasic
    #    0      -3.414590    0.000000
    #    1      -3.421066    0.000000
    #    2      -3.427541    1.779744
    #    3      -3.434015    1.788931
    #    4      -3.440489    1.798100
    #    ...          ...         ...
    #    29995 -34.383953   34.046697
    #    29996 -34.384913   34.044347
    #    29997 -34.385873   34.041977
    #    29998 -34.386833   34.039588
    #    29999 -34.387793   34.037179
    #
    # Based on my understanding of this function, neither of these look correct, but at least the
    # other ABIs meet the requirement that tonic + phasic == input, because the input ranges from
    # about 0 to 5.
    def test_eda_phasic(self):
        try:
            import neurokit2 as nk
        except ImportError:
            self.skipTest("requires neurokit2")

        sampling_rate = 1000
        eda = nk.eda_simulate(duration=30, sampling_rate=sampling_rate, scr_number=6,
                              noise=0.01, drift=0.01, random_state=42)
        cvxEDA = nk.eda_phasic(nk.standardize(eda), method="cvxeda")
        assert len(cvxEDA) == len(eda)
        print(cvxEDA)
