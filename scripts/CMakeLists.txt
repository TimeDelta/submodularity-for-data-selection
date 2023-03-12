add_executable(mfw most_freq_words.cpp)
target_link_libraries(mfw boost_program_options)

if(UNIX)
	add_executable(shuffle_lines shuffle_lines.cpp)
	
	add_executable(filter Filter.cpp)
	target_link_libraries(filter boost_program_options)
	
	add_subdirectory(opengrm-ngram)
endif()
