Extract Crystax 10.3.2 to $CRYSTAX_DIR
Extract Python source to $PYTHON_DIR

cd target/crystax

For Python 3.6, run the following extra commands, derived from
https://github.com/inclement/crystax_python_builds:

    patch -t -d $PYTHON_DIR -p1 -i patch_python3.6.patch
    cp android.mk.3.6 config.c.3.6 interpreter.c.3.6 $CRYSTAX_DIR/build/tools/build-target-python
    mkdir $CRYSTAX_DIR/sources/python/3.6
    cp sources-Android.mk.3.6 $CRYSTAX_DIR/sources/python/3.6/Android.mk

./build-target-python.sh --abis=armeabi-v7a,x86 --verbose $PYTHON_DIR

The Python libraries and includes will now be in $CRYSTAX_DIR/sources/python. These should be
packaged for the Maven repository by package-target.sh, and copied to other machines where Chaqupy
itself may be built.
