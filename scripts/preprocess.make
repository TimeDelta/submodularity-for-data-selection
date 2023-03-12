CORPUS_FILES  =
CLEANED_FILES = $(addsuffix .cleaned,$(CORPUS_FILES))

.SECONDARY:
.PHONY: combined cleaned help
cleaned: $(CLEANED_FILES)
combined: $(OUTPUT)
help:
	@echo Targets: cleaned combined help

# rule to clean a file
%.cleaned: % $(SCRIPTS_DIR)/normalize-punctuation.perl $(SCRIPTS_DIR)/tokenizer.perl $(SCRIPTS_DIR)/clean_text.py
	@echo Cleaning `basename "$<"`
	@$(BUILD_DIR)/utilities/c_submit.py -e $@.errors -j "$@.job" $(SCRIPTS_DIR)/condor_clean -h "$(HOME)" "$(SCRIPTS_DIR)" "$(abspath $<)" "$(abspath $@)"
	$(DBG)rm "$@.errors" "$@.job"

$(OUTPUT): $(CLEANED_FILES)
	@echo Combining cleaned chunks
	@cat $(CLEANED_FILES) > $(OUTPUT)
