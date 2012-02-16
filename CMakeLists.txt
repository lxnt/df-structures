PROJECT(dfapi)

CMAKE_MINIMUM_REQUIRED(VERSION 2.8)

if(DFHACK_DATA_DESTINATION)
    set(DFAPI_DATA_DESTINATION ${DFHACK_DATA_DESTINATION})
else()
    set(DFAPI_DATA_DESTINATION "lib" CACHE FILEPATH "where to put symbols.xml") 
endif()


SET(PERL_EXECUTABLE "perl" CACHE FILEPATH 
    "This is the perl executable to run in the codegen step. Tweak it if you need to run a specific one."
)

execute_process(COMMAND ${PERL_EXECUTABLE} xml/list.pl xml include/df ";"
                WORKING_DIRECTORY ${dfapi_SOURCE_DIR}
                OUTPUT_VARIABLE GENERATED_HDRS)
                
IF(UNIX)
    SET(CMAKE_CXX_FLAGS_DEBUG "-g -Wall")
    SET(CMAKE_CXX_FLAGS "-fvisibility=hidden -m32 -march=i686 -mtune=generic -std=c++0x")
    SET(CMAKE_C_FLAGS "-fvisibility=hidden -m32 -march=i686 -mtune=generic")
ENDIF()

IF(NOT DEFINED CMAKE_BUILD_TYPE OR CMAKE_BUILD_TYPE STREQUAL "")
    SET(CMAKE_BUILD_TYPE "Release" CACHE STRING 
        "Choose the type of build, options are: Debug Release RelWithDebInfo."
    )
ENDIF()

INCLUDE_DIRECTORIES(include)
IF(UNIX)
    add_definitions(-DLINUX_BUILD)
    SET(CMAKE_C_FLAGS "-m32")
ENDIF()

SET (SRC_DFAPI
    src/virtual_identity.cpp
    src/dfapi.cpp
)

# Generation

SET_SOURCE_FILES_PROPERTIES(${GENERATED_HDRS} PROPERTIES HEADER_FILE_ONLY TRUE GENERATED TRUE)

FILE(GLOB GENERATE_INPUT_SCRIPTS ${dfapi_SOURCE_DIR}/xml/*.pm ${dfapi_SOURCE_DIR}/xml/*.xslt)
FILE(GLOB GENERATE_INPUT_XMLS ${dfapi_SOURCE_DIR}/xml/*.xml)

ADD_CUSTOM_COMMAND(
    OUTPUT ${dfapi_SOURCE_DIR}/include/df/static.inc
    COMMAND ${PERL_EXECUTABLE} xml/codegen.pl xml include/df
    WORKING_DIRECTORY ${dfapi_SOURCE_DIR}
    MAIN_DEPENDENCY ${dfapi_SOURCE_DIR}/xml/codegen.pl
    DEPENDS ${GENERATE_INPUT_XMLS} ${GENERATE_INPUT_SCRIPTS}
)

ADD_CUSTOM_TARGET(generate_headers DEPENDS ${dfapi_SOURCE_DIR}/include/df/static.inc)
ADD_LIBRARY ( dfapi ${SRC_DFAPI} )
ADD_DEPENDENCIES(dfapi generate_headers)

install(FILES xml/symbols.xml DESTINATION ${DFAPI_DATA_DESTINATION})
