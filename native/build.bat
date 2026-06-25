@echo off
REM ZICORE Native Module Build Script (Windows)
REM Builds Rust avionics library and C++ CFD module

echo ======================================
echo  ZICORE Native Module Builder v0.1
echo ======================================

REM Check for Rust
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Rust/Cargo not found. Install from https://rustup.rs
    echo [!] Skipping Rust avionics build
    set RUST_OK=0
) else (
    echo [+] Rust found
    set RUST_OK=1
)

REM Check for C++ compiler
where cl >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where g++ >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [!] No C++ compiler found. Install MSVC or MinGW.
        echo [!] Skipping C++ CFD build
        set CPP_OK=0
    ) else (
        echo [+] g++ found
        set CPP_OK=1
    )
) else (
    echo [+] MSVC found
    set CPP_OK=1
)

REM Build Rust avionics library
if "%RUST_OK%"=="1" (
    echo.
    echo --- Building Rust Avionics Library ---
    cd native
    cargo build --release
    if %ERRORLEVEL% equ 0 (
        echo [+] Rust library built successfully
        copy target\release\zicore_avionics.dll ..\ 2>nul
        copy target\release\libzicore_avionics.so ..\ 2>nul
    ) else (
        echo [-] Rust build failed
    )
    cd ..
)

REM Build C++ CFD module
if "%CPP_OK%"=="1" (
    echo.
    echo --- Building C++ CFD Module ---
    pip install pybind11
    python -m pybind11 --includes
    python -c "import pybind11; print(pybind11.get_include())" > nul 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [+] Building CFD module with pybind11...
        python setup.py build_ext --inplace 2>nul
        if %ERRORLEVEL% equ 0 (
            echo [+] C++ CFD module built successfully
        ) else (
            echo [-] C++ build failed (install pybind11: pip install pybind11)
        )
    ) else (
        echo [-] pybind11 not available
    )
)

echo.
echo ======================================
echo  Build Complete
echo ======================================
echo.
echo Pure Python fallbacks are available for all modules.
echo Install Rust and C++ compilers for native performance.
pause
