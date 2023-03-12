#include <cstdlib>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <vector>
#include <map>
#include <boost/program_options.hpp>

void printMostFreq(std::ifstream& f, unsigned int numWords, bool printCounts){
	std::map<std::string, int> wordCounts;
	std::string word;
	
	while (f >> word)
		++wordCounts[word];
	
	std::vector<std::pair<std::string, int> > wordVector(numWords);
	std::partial_sort_copy(
		wordCounts.begin(),
		wordCounts.end(),
		wordVector.begin(),
		wordVector.end(),
		[](const std::pair<std::string,int>& x, const std::pair<std::string,int>& y){
			return x.second > y.second;
		}
	);
	
	for (unsigned int i = 0; i < wordVector.size() && i < numWords; ++i){
		std::cout << wordVector[i].first;
		if (printCounts)
			std::cout << "\t" << wordVector[i].second;
		std::cout << std::endl;
	}
}


int main(int argc, char const *argv[]) {
	namespace po = boost::program_options;
	
	bool printCounts = false;
	int numWords = 0;
	std::string fname;
	
	po::options_description desc("Options");
	desc.add_options()
		("help", "Prints help message")
		("c", po::bool_switch(&printCounts), "Prints word counts")
		("file", po::value<std::string>(&fname)->required(), "Text file to read")
		("count", po::value<int>(&numWords)->required(), "Max number of words to include in the output")
	;
	po::positional_options_description pos;
	pos.add("file", 1);
	pos.add("count", 1);
	
	po::variables_map vm;
	
	try {
		po::store(po::command_line_parser(argc, argv).options(desc).positional(pos).run(), vm);
		if (vm.count("help")) {
			std::cout << desc << std::endl;
			return 0;
		}
		po::notify(vm); // throws on error, so do after help in case there are any problems
	} catch (boost::program_options::error& e) {
		std::cerr << "ERROR: " << e.what() << std::endl << std::endl;
		std::cout << desc << std::endl;
		return 1;
	}
	
	std::ifstream f(argv[1]);
	if (!f) {
		printf("File does not exist");
		return 1;
	} else
		printMostFreq(f, std::atoi(argv[2]), printCounts);
	return 0;
}
