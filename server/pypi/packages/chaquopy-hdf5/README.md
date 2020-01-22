The following is the process for generating files needed for a new ABI. For more details, see
[here](http://hdf-forum.184993.n3.nabble.com/HDF5-cross-compile-error-configure-23533-error-cannot-run-test-program-while-cross-compiling-td4027685.html.

Run the build. If the ABI is unknown it will fail, but should generate the following files in
`src/src`:

    H5detect
    H5make_libsettings
    libhdf5.settings

Copy these files to an Android device or emulator for this ABI, to the directory
`/data/local/tmp` (`/sdcard` is probably mounted noexec).

Open a shell on the device, and run the following:

    cd /data/local/tmp
    LD_LIBRARY_PATH=. ./H5detect > H5Tinit.c
    LD_LIBRARY_PATH=. ./H5make_libsettings > H5lib_settings.c

Copy the generated files into the `generated` subdirectory next to this README, and run the
build again. Don't forget to commit the files once it succeeds.
