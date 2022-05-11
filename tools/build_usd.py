#**********************************************************************
# Copyright 2020 Advanced Micro Devices, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#********************************************************************
import sys
import os
from pathlib import Path

from build import rm_dir, check_call, OS


def main(bin_dir, clean, build_var, *args):
    if len(args) == 1 and args[0] in ("--help", "-h"):
        print("""
Usage

  build_usd.py <bin-dir> [<args-for-USD/build_scripts/build_usd.py>...]
  
Specify arguments for build_scripts/build_usd.py script
in USD repository.
""")
        return

    repo_dir = Path(__file__).parent.parent
    usd_dir = repo_dir / "deps/USD"

    if clean:
        rm_dir(bin_dir / "USD")

    cur_dir = os.getcwd()
    os.chdir(str(usd_dir))

    try:
        # applying patch data/USD_MaterialX.patch
        # Temporary implements https://github.com/PixarAnimationStudios/USD/pull/1610
        # TODO: remove this after up USD to >= 2203 and implement their own fix
        #  https://github.com/PixarAnimationStudios/USD/commit/adfc04eea92b91965b0da68503539b079a5d30d9
        # check_call('git', 'apply', '--whitespace=nowarn', str(repo_dir / "tools/data/USD_MaterialX.patch"))

        # applying patch data/USD_deps.patch
        # fixes issues with building USD on python 3.10
        check_call('git', 'apply', str(repo_dir / "tools/data/USD_deps.patch"))

        check_call('git', 'apply', str(repo_dir / "tools/data/usd.diff"))

        # modifying pxr/usdImaging/CMakeLists.txt
#         usd_imaging_lite_path = repo_dir / "deps/UsdImagingLite/pxr/usdImaging/usdImagingLite"
#
#         usd_imaging_cmake = usd_dir / "pxr/usdImaging/CMakeLists.txt"
#         print("Modifying:", usd_imaging_cmake)
#         cmake_txt = usd_imaging_cmake.read_text()
#         usd_imaging_cmake.write_text(cmake_txt + f"""
# add_subdirectory("{usd_imaging_lite_path.absolute().as_posix()}" usdImagingLite)
#         """)

        bin_usd_dir = bin_dir / "USD"
        build_args = [f'MATERIALX,-DMATERIALX_BUILD_PYTHON=ON -DMATERIALX_INSTALL_PYTHON=OFF '
                      f'-DMATERIALX_PYTHON_EXECUTABLE="{sys.executable}"']

        blender_lib_folder = "C:/GPUOpen/Blender/lib/win64_vc15"

        build_args.append(f'USD,-DBoost_COMPILER:STRING=-vc142 -DBoost_USE_MULTITHREADED=ON -DBoost_USE_STATIC_LIBS=ON '
                          f'-DBoost_USE_STATIC_RUNTIME=OFF -DBOOST_ROOT="{blender_lib_folder}/boost" '
                          f'-DBoost_NO_SYSTEM_PATHS=ON -DBoost_NO_BOOST_CMAKE=ON '
                          f'-DBoost_ADDITIONAL_VERSIONS=1.78 -DBOOST_LIBRARYDIR="{blender_lib_folder}/boost/lib" '
                          f'-DPYTHON_EXECUTABLE="{sys.executable}" -DPXR_ENABLE_PYTHON_SUPPORT=OFF '
                          f'-DPXR_SET_INTERNAL_NAMESPACE="usdBlender" -DOPENSUBDIV_ROOT_DIR="{blender_lib_folder}/opensubdiv" '
                          f'-DOpenImageIO_ROOT="{blender_lib_folder}/openimageio" '
                          f'-DOPENEXR_LIBRARIES="{blender_lib_folder}/imath/lib/Imath_s.lib" '
                          f'-DOPENEXR_INCLUDE_DIR="{blender_lib_folder}/imath/include" -DPXR_ENABLE_OSL_SUPPORT=OFF '
                          f'-DPXR_BUILD_OPENCOLORIO_PLUGIN=OFF -DPXR_ENABLE_PTEX_SUPPORT=OFF -DPXR_BUILD_USD_TOOLS=OFF '
                          f'-DCMAKE_DEBUG_POSTFIX="_d" -DBUILD_SHARED_LIBS=Off '
                          f'-DPXR_MONOLITHIC_IMPORT="C:/GPUOpen/BlenderUSDHydraAddon/deps/USD/cmake/defaults/Version.cmake" '
                          f'-DTBB_INCLUDE_DIRS="{blender_lib_folder}/tbb/include" '
                          f'-DTBB_LIBRARIES="{blender_lib_folder}/tbb/lib/tbb.lib" '
                          f'-DTbb_TBB_LIBRARY="{blender_lib_folder}/tbb/lib/tbb.lib" '
                          f'-DTbb_TBB_LIBRARY="{blender_lib_folder}/tbb/lib/tbb_debug.lib" ')

        if build_var == 'relwithdebuginfo' and OS == 'Windows':
            # disabling optimization for debug purposes
            build_args.append(f'USD,-DCMAKE_CXX_FLAGS_RELWITHDEBINFO="/Od"')

        call_args = (sys.executable, str(usd_dir / "build_scripts/build_usd.py"),
                     '--verbose',
                     '--build', str(bin_usd_dir / "build"),
                     '--src', str(bin_usd_dir / "deps"),
                     '--materialx',
                     '--openvdb',
                     '--build-args', *build_args,
                     '--no-python',
                     '--build-monolithic',
                     '--build-variant', build_var,
                     str(bin_usd_dir / "install"),
                     *args)

        try:
            check_call(*call_args)

        finally:
            print("Reverting USD repo")
            check_call('git', 'checkout', '--', '*')
            check_call('git', 'clean', '-f')

    finally:
        os.chdir(cur_dir)


if __name__ == "__main__":
    main(*sys.argv[1:])
