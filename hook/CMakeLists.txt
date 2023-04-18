cmake_minimum_required(VERSION 3.0.0)
project(hook VERSION 0.1.0)


add_executable(test  test.cpp)
add_library (hook SHARED hook.cpp)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
