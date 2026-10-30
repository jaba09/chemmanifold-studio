E=/opt/ofb/env
[ -e $E/lib/sys-mpich ] || ln -s mpich-3.3 $E/lib/sys-mpich
export PATH=$E/bin:$PATH
export LD_LIBRARY_PATH=$E/lib/sys-mpich:$E/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export WM_PROJECT_DIR=$E FOAM_ETC=$E/etc FI_PROVIDER=tcp
export LD_LIBRARY_PATH=/root/OpenFOAM/user-v2412/platforms/linux64GccDPInt32Opt/lib:$LD_LIBRARY_PATH
