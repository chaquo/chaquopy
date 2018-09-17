This is a very complex build, and when a command fails you might want an explanation of why
it's even being run. The following command will provide that (FIXME move env vars and options
to rc file):

    <env_vars> bazel cquery <options> "somepath(<src>, <dst>)"

`<env_vars>` are all variables which could affect the build: currently `SRC_DIR` and
`CHAQUOPY_PYTHON_*`.

<options> are all the options to `bazel build`, other than those like `--subcommands` and
--verbose_failures` which only apply when you're actually doing a build.

<src> is the target you want to build, e.g. `//tensorflow/tools/pip_package:build_pip_package`.

<tgt> is the target you want an explanation for. This is shown immediately after the word
"SUBCOMMAND" in the `bazel build` output. If the SUBCOMMAND line says "[for host]", then
write this as `config(<tgt>, host)`.
