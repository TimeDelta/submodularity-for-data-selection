# see create_lm script for example of this script's usage

# file suffixes
0COUNTS_FILE_SUFFIX     = .0counts
NON0COUNTS_FILE_SUFFIX  = .non0counts
DICT_COUNTS_FILE_SUFFIX = .dict_counts
# COUNTS_FILE_SUFFIX is used to store the file suffix for the dependencies of the dictionary-restricted count files
ifdef $(and VOCAB,RM_0COUNTS)
COUNTS_FILE_SUFFIX = $(NON0COUNTS_FILE_SUFFIX)
else
COUNTS_FILE_SUFFIX = $(0COUNTS_FILE_SUFFIX)
endif

# files
CORPUS_FILES      =
0COUNTS_FILES     = $(addsuffix $(0COUNTS_FILE_SUFFIX),$(CORPUS_FILES))
NON0COUNTS_FILES  = $(0COUNTS_FILES:$(0COUNTS_FILE_SUFFIX)=$(NON0COUNTS_FILE_SUFFIX))
# FINAL_FILES is used to the dependencies for the final combined_counts file
ifdef DICT
FINAL_FILES       = $(NON0COUNTS_FILES:$(NON0COUNTS_FILE_SUFFIX)=$(DICT_COUNTS_FILE_SUFFIX))
else
FINAL_FILES       = $(NON0COUNTS_FILES:$(NON0COUNTS_FILE_SUFFIX)=$(COUNTS_FILE_SUFFIX))
endif

ifdef DEBUG
$(warning CORPUS_FILES      = $(CORPUS_FILES))
$(warning 0COUNTS_FILES     = $(0COUNTS_FILES))
$(warning NON0COUNTS_FILES  = $(NON0COUNTS_FILES))
$(warning FINAL_FILES       = $(FINAL_FILES))
else
DBG = @
endif

# directories
SCRIPTS_DIR = $(scripts)
MITLM_DIR   = $(SCRIPTS_DIR)/mitlm

# count options
VOCAB =
ORDER =

# the following line prevents make from deleting intermediate files
.SECONDARY:
.PHONY: counts
counts: $(COMBINED_COUNTS)

%$(0COUNTS_FILE_SUFFIX): %
	@echo Calculating counts for `basename "$<"`
	$(DBG)$(BUILD_DIR)/utilities/c_submit.py -e "$@.errors" -j "$@.job" -m $$((`du -m --apparent-size "$<" | awk '{print $$1}'`+500)) "$(MITLM_DIR)/estimate-ngram" $(VOCAB) $(ORDER) -verbose 0 -wc "$(abspath $@)" -t "$(abspath $<)"
	$(DBG)rm "$@.errors" "$@.job"

%$(NON0COUNTS_FILE_SUFFIX): %$(0COUNTS_FILE_SUFFIX)
	@echo Removing n-grams that do not occur in `basename "$(subst $(0COUNTS_FILE_SUFFIX),,$<)"`
	$(DBG)$(BUILD_DIR)/utilities/c_submit.py -e "$@.errors" -j "$@.job" $(SCRIPTS_DIR)/condor_redirect $(abspath $@) /usr/bin/awk '$$NF!~/^0$$/' $(abspath $<) # must use $$ to get a single $
	$(DBG)rm "$@.errors" "$@.job"

%$(DICT_COUNTS_FILE_SUFFIX): %$(COUNTS_FILE_SUFFIX)
	@echo Limiting counts for `basename "$(subst $(COUNTS_FILE_SUFFIX),,$<)"` based on pronunciation dictionary
	$(DBG)$(BUILD_DIR)/utilities/c_submit.py -e "$@.errors" -j "$@.job" $(SCRIPTS_DIR)/condor_redirect $(abspath $@) $(SCRIPTS_DIR)/limit_counts_by_dict --dict "$(DICT)" --counts "$(abspath $<)"
	$(DBG)rm "$@.errors" "$@.job"

$(COMBINED_COUNTS): $(FINAL_FILES)
	@echo Merging counts
	$(DBG)if [ -n "`echo "$(CORPUS_FILES)" | grep ' '`" ]; then \
		$(MITLM_DIR)/estimate-ngram -verbose 0 $(ORDER) -c "`echo "$(FINAL_FILES)" | sed 's/ /, /g'`" -wc "$@"; \
	else \
		ln -fs "$(FINAL_FILES)" "$@"; \
	fi
