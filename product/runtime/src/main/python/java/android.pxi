from cpython.bytes cimport PyBytes_FromStringAndSize
from posix.types cimport off_t

cdef extern from *:
    """
    #ifdef __ANDROID__
    #include "android/asset_manager.h"
    #include "android/asset_manager_jni.h"

    #else
    // This file will never be used on non-Android platforms, but stub out the asset APIs
    // to allow it to compile.
    struct AAssetManager;
    struct AAsset;
    enum { AASSET_MODE_UNKNOWN, AASSET_MODE_RANDOM, AASSET_MODE_STREAMING, AASSET_MODE_BUFFER };

    #define AAssetManager_fromJava(...) NULL
    #define AAssetManager_open(...) NULL
    #define AAsset_close(...) 0
    #define AAsset_getLength(...) 0
    #define AAsset_getRemainingLength(...) 0
    #define AAsset_read(...) 0
    #define AAsset_seek(...) 0
    #endif
    """
    struct AAssetManager:
        pass
    struct AAsset:
        pass
    enum: AASSET_MODE_UNKNOWN, AASSET_MODE_RANDOM, AASSET_MODE_STREAMING, AASSET_MODE_BUFFER

    AAssetManager* AAssetManager_fromJava(JNIEnv* env, jobject assetManager)
    AAsset* AAssetManager_open(AAssetManager* mgr, const char* filename, int mode)
    void AAsset_close(AAsset* asset)
    off_t AAsset_getLength(AAsset* asset)
    off_t AAsset_getRemainingLength(AAsset* asset)
    int AAsset_read(AAsset* asset, void* buf, size_t count)
    off_t AAsset_seek(AAsset* asset, off_t offset, int whence)


cdef class AssetFile(object):
    cdef AAsset *asset
    cdef str path

    def __init__(self, context, path):
        self.path = path
        j_mgr = <JNIRef?>context.getAssets()._chaquopy_this
        mgr = AAssetManager_fromJava(get_jnienv(), j_mgr.obj)
        if mgr == NULL:
            raise Exception("AAssetManager_fromJava failed")

        self.asset = AAssetManager_open(mgr, path.encode(), AASSET_MODE_RANDOM)
        if self.asset == NULL:
            raise FileNotFoundError(path)

    def __repr__(self):
        return f"{type(self).__name__}({self.path!r})"

    def read(self, int size=-1):
        self.assert_open()
        if size < 0:
            size = AAsset_getRemainingLength(self.asset)
            need_all = True
        else:
            need_all = False

        buf = PyBytes_FromStringAndSize(NULL, size)
        actual_size = AAsset_read(self.asset, <char*>buf, size)
        if actual_size < 0:
            raise Exception("AAsset_read failed")
        elif actual_size < size:
            if need_all:
                raise Exception(f"AAsset_read: requested all remaining bytes ({size}) "
                                f"but only got {actual_size}")
            else:
                return buf[:actual_size]
        else:
            return buf

    def seekable(self):
        return True

    def seek(self, offset, whence=os.SEEK_SET):
        self.assert_open()
        result = AAsset_seek(self.asset, offset, whence)
        if result < 0:
            # zipfile expects this exception type when seeking out of range.
            raise OSError(f"seek({offset}, {whence}) failed at offset {self.tell()} "
                          f"in {self.path!r}")
        return result

    def tell(self):
        self.assert_open()
        return AAsset_getLength(self.asset) - AAsset_getRemainingLength(self.asset)

    def close(self):
        if self.asset != NULL:
            AAsset_close(self.asset)
            self.asset = NULL

    cdef assert_open(self):
        if self.asset == NULL:
            raise ValueError("Asset is closed")
