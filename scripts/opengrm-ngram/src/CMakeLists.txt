project (OpenGrm CXX)

if (UNIX)
	SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-sign-compare -Wno-maybe-uninitialized -Wno-unused-but-set-variable")
endif()

macro(add_library_installed libname)
add_library (${libname} ${ARGN})
install (TARGETS ${libname} DESTINATION lib)
endmacro(add_library_installed libname)

macro(add_executable_installed execname)
add_executable (${execname} ${ARGN})
set_target_properties(${execname} PROPERTIES LINKER_LANGUAGE CXX)
install (TARGETS ${execname} DESTINATION bin)
endmacro(add_executable_installed execname)

include_directories (SYSTEM ${PROJECT_SOURCE_DIR}/include)

add_subdirectory (lib)
add_subdirectory (bin)

