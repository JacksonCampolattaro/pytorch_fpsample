import os
import platform
import sys
from setuptools import find_packages, setup
from torch.__config__ import parallel_info
from torch.utils import cpp_extension
import torch

__version__ = "0.1.0"
WITH_CUDA = False

sources = [
    "csrc/fpsample.cpp",
    "csrc/fpsample_autograd.cpp",
    "csrc/fpsample_meta.cpp",
    "csrc/cpu/fpsample_cpu.cpp",
    "csrc/cpu/bucket_fps/wrapper.cpp",
]

# ── 1. Start from PyTorch's own flags so ABI tags always match ──────────────
extra_compile_args = {"cxx": list(cpp_extension._get_build_directory.__module__ and
                                   torch._C._GLIBCXX_USE_CXX11_ABI and [] or [])}

# Detect the CXX11 ABI flag PyTorch itself was built with and mirror it
cxx11_abi = torch.compiled_with_cxx11_abi()
extra_compile_args = {
    "cxx": [
        "-O3",
        f"-D_GLIBCXX_USE_CXX11_ABI={int(cxx11_abi)}",  # must match PyTorch's own build
        "-std=c++17",                                    # explicit standard avoids compiler default drift
    ]
}
extra_link_args = []

# ── 2. OpenMP ────────────────────────────────────────────────────────────────
info = parallel_info()
if (
    "backend: OpenMP" in info
    and "OpenMP not found" not in info
    and sys.platform != "darwin"
):
    extra_compile_args["cxx"] += ["-DAT_PARALLEL_OPENMP"]
    if sys.platform == "win32":
        extra_compile_args["cxx"] += ["/openmp"]
    else:
        extra_compile_args["cxx"] += ["-fopenmp"]
    extra_link_args += ["-fopenmp"]   # also needed at link time on Linux
else:
    print("Compiling without OpenMP...")

# ── 3. macOS / arm64 ─────────────────────────────────────────────────────────
if sys.platform == "darwin":
    extra_compile_args["cxx"] += ["-D_LIBCPP_DISABLE_AVAILABILITY"]
    if platform.machine() == "arm64":
        extra_compile_args["cxx"] += ["-arch", "arm64"]
        extra_link_args += ["-arch", "arm64"]

# ── 4. Extension definition ──────────────────────────────────────────────────
if WITH_CUDA:
    raise NotImplementedError("CUDA is not supported yet.")
else:
    ext_modules = [
        cpp_extension.CppExtension(
            name="torch_fpsample._core",
            include_dirs=["csrc"],
            sources=sources,
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
        )
    ]

# ── 5. ABI-safe BuildExtension ───────────────────────────────────────────────
build_ext_cmd = cpp_extension.BuildExtension.with_options(
    no_python_abi_suffix=False,   # keeps the cpython-3XX-… tag → prevents silent misloads
    use_ninja=True,               # faster and more reliable than make
)

setup(
    name="torch_fpsample",
    version=__version__,
    author="Leonard Lin",
    author_email="leonard.keilin@gmail.com",
    description="PyTorch implementation of fpsample.",
    ext_modules=ext_modules,
    keywords=["pytorch", "farthest", "furthest", "sampling", "sample", "fps"],
    packages=find_packages(),
    package_data={"": ["*.pyi"]},
    cmdclass={"build_ext": build_ext_cmd},
    python_requires=">=3.8",
    install_requires=["torch>=2.0"],
)
