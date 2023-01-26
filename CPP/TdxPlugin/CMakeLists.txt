cmake_minimum_required(VERSION 3.0.0)
project(tdxplugins VERSION 0.1.0)


add_library(tdxpluginvs SHARED sqlite/sqlite3.c comm.cpp  hgt.cpp dllmain.cpp)
add_executable(main comm.cpp sqlite/sqlite3.c  hgt.cpp dllmain.cpp xxv.cpp)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
