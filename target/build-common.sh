sysroot=$toolchain/sysroot
host_triplet=$(cd $toolchain/bin && echo *-clang | sed 's/-clang$//')
