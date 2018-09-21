Because of the way in which the build generates the Python public API files
(tensorflow/python/tools/api/generator/create_python_api.py), everything will be built twice:
once for the build machine and once for the target. If you want to complete the build in less
than an hour, you'll probably need a machine with at least 6 cores.

The following things must be installed before starting the build:

* Bazel: the [installation instructions for
  Ubuntu](https://docs.bazel.build/versions/master/install-ubuntu.html#install-with-installer-ubuntu)
  also work on Debian.

* g++ and binutils for the build machine.

* NumPy must be installed in whichever Python environment is launched by the command "python".

This is a very complex build, and when a command fails you might want an explanation of why
it's even being run. The following command will provide that:

    bazel cquery <options> "somepath(<tgt1>, <tgt2>)"

Where:

* `<options>` are the options used for `bazel build` in `build.sh`.

* `<tgt1>` is the target you want to build, e.g.
  `//tensorflow/tools/pip_package:build_pip_package`.

* `<tgt2>` is the target you want an explanation for. The target corresponding to each command
  is shown immediately after the word "SUBCOMMAND" in the `bazel build` output. If the
  SUBCOMMAND line says "[for host]", then use the syntax `config(<tgt2>, host)`.
