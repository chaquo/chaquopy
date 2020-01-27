See https://www.tensorflow.org/install/source for a summary of how the build works.

Because of the way in which the build generates the Python public API files
(`tensorflow/python/tools/api/generator/create_python_api.py`), everything will be built twice:
once for the build machine and once for the target. Use a machine with as many cores as
possible.

The following things must be installed before starting the build:

* Bazel: the easiest way is to download [Bazelisk](https://github.com/bazelbuild/bazelisk).
* g++, binutils and python3-dev for the build machine.
* NumPy must be installed in whichever Python environment is launched by the command "python".

If a build step fails you might want an explanation of why it's being run. The following
command will provide that:

    bazel cquery <options> "somepath(<tgt1>, <tgt2>)"

Where:

* `<options>` are the options used for `bazel build` in `build.sh`.

* `<tgt1>` is the target you want to build, e.g.
  `//tensorflow/tools/pip_package:build_pip_package`.

* `<tgt2>` is the target you want an explanation for. This is the string shown immediately
  after the word "SUBCOMMAND" in the build output. If the SUBCOMMAND line says "[for host]",
  then use the syntax `config(<tgt2>, host)`.
