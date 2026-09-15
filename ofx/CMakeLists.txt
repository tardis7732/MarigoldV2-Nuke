cmake_minimum_required(VERSION 3.20)
project(MarigoldV2NormalsOFX CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_library(MarigoldV2Normals SHARED src/marigold_ofx.cpp)
target_include_directories(MarigoldV2Normals PRIVATE include/openfx)

if(WIN32)
  target_link_libraries(MarigoldV2Normals PRIVATE ws2_32)
  set(OFX_ARCH_DIR "Win64")
  if(MSVC)
    target_compile_options(MarigoldV2Normals PRIVATE /W3 /O2 /utf-8)
  endif()
else()
  set(OFX_ARCH_DIR "Linux-x86-64")
  target_compile_options(MarigoldV2Normals PRIVATE -Wall -O2 -fvisibility=hidden -fPIC)
  target_link_libraries(MarigoldV2Normals PRIVATE dl pthread)
  # keep every symbol but the OFX entry points private, and avoid depending
  # on a newer libstdc++ than the host ships
  target_link_options(MarigoldV2Normals PRIVATE -Wl,--exclude-libs,ALL -static-libstdc++ -static-libgcc)
endif()

# OFX bundle layout: MarigoldV2Normals.ofx.bundle/Contents/<arch>/MarigoldV2Normals.ofx
set(BUNDLE_DIR "${CMAKE_BINARY_DIR}/MarigoldV2Normals.ofx.bundle/Contents/${OFX_ARCH_DIR}")
set_target_properties(MarigoldV2Normals PROPERTIES
  PREFIX ""
  SUFFIX ".ofx"
  RUNTIME_OUTPUT_DIRECTORY "${BUNDLE_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_RELEASE "${BUNDLE_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_DEBUG "${BUNDLE_DIR}"
  RUNTIME_OUTPUT_DIRECTORY_RELWITHDEBINFO "${BUNDLE_DIR}"
  LIBRARY_OUTPUT_DIRECTORY "${BUNDLE_DIR}")

# ---- test host (not part of the bundle) ------------------------------------
option(MARIGOLDV2_BUILD_TESTS "build the mini OFX host used by ofx/tests" ON)
if(MARIGOLDV2_BUILD_TESTS)
  add_executable(mini_host tests/mini_host.cpp)
  target_include_directories(mini_host PRIVATE include/openfx)
  if(NOT WIN32)
    target_link_libraries(mini_host PRIVATE dl)
  endif()
  set_target_properties(mini_host PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/tests")
endif()
