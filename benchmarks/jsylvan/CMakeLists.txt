cmake_minimum_required(VERSION 3.17)
project(jsylvan_adapter LANGUAGES C)
find_package(JNI REQUIRED)
find_package(Threads REQUIRED)
add_library(sylvan-java SHARED
    "${UPSTREAM_ROOT}/src/main/c/sylvan-java/src/jsylvan.c"
    "${UPSTREAM_ROOT}/src/main/c/sylvan-java/src/mc_help.c")
target_include_directories(sylvan-java PRIVATE ${JNI_INCLUDE_DIRS} "${SYLVAN_ROOT}/src")
target_link_libraries(sylvan-java PRIVATE "${SYLVAN_LIBRARY}" Threads::Threads gmp m rt)
