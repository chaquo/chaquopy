case ${abi:?} in
    armeabi-v7a)
        HOST=arm-linux-androideabi
        ;;
    arm64-v8a)
        HOST=aarch64-linux-android
        ;;
    x86)
        HOST=i686-linux-android
        ;;
    x86_64)
        HOST=x86_64-linux-android
        ;;
    *)
        echo "Unknown ABI: '$abi'"
        exit 1
        ;;
esac
