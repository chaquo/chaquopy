sysroot=$toolchain/sysroot
host_triplet=$(cd $toolchain/bin && echo *-gcc | sed 's/-gcc$//')
