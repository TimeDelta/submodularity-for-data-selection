#include <fstream>
#include <iostream>
#include <cstring>
#include <vector>
#include <algorithm>

using std::cout;
using std::endl;

typedef unsigned long int Index;

int main(int argc, char const *argv[])
{
	if (argc < 2 || strcmp(argv[1], "--help") == 0){
		cout << "This is a memory-efficient line shuffling algorithm.\n"
		     << "It reads from a file and outputs to stdout.\n"
		     << "Usage: " << argv[0] << " <file>\n";
		return 0;
	}
	std::string fileName = argv[1];
	std::ifstream file(fileName.c_str(), std::ifstream::in);
	
	// first, find all of the line markers
	std::vector<Index> lineStartOffsets;
	std::string line;
	while (!file.eof()) {
		lineStartOffsets.push_back(file.tellg());
		std::getline(file, line); // don't actually care what the line is yet
		file.peek();
	}
	
	// randomly shuffle the line numbers
	std::random_shuffle(lineStartOffsets.begin(), lineStartOffsets.end());
	
	for (auto offset : lineStartOffsets){
		file.seekg(offset);
		std::getline(file, line);
		cout << line << endl;
	}
	
	file.close();
	
	return 0;
}
