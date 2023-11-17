cmake_minimum_required(VERSION 3.28)
project(protobuf_gen)

set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_executable(${PROJECT_NAME} main.cpp)


find_package(protobuf CONFIG REQUIRED)
target_link_libraries(${PROJECT_NAME} PRIVATE protobuf::libprotobuf)

set(PROTO_FILES protobufs.proto)
protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ${PROTO_FILES})
target_sources(${PROJECT_NAME} PRIVATE ${PROTO_SRCS} ${PROTO_HDRS})