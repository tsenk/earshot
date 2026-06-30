cmake_minimum_required(VERSION 3.27)

project(earshot LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT DEFINED SKBUILD_PROJECT_NAME)
	message(FATAL_ERROR "This project must be built via scikit-build-core (pip install / uv sync).")
endif()

find_package(Python 3.11 REQUIRED COMPONENTS Interpreter Development.Module)

execute_process(
	COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
	OUTPUT_STRIP_TRAILING_WHITESPACE
	OUTPUT_VARIABLE NB_DIR
)
list(APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
find_package(nanobind CONFIG REQUIRED)

add_compile_options(/W4 /permissive-)

add_subdirectory(src/native/audio)
