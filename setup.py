from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_include

ext_modules = [
    Pybind11Extension(
        "zicore_cfd",
        ["native/cfd_module.cpp"],
        include_dirs=[get_include()],
        language="c++",
        extra_compile_args=["-std=c++17", "/O2", "/fp:fast"],
    ),
]

setup(
    name="zicore_cfd",
    version="0.1.0",
    description="ZICORE C++ CFD Simulation Module",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
