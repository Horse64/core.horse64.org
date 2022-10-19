
.PHONY: .test-translator

intro-message:
	@echo -e "\033[95;40mWelcome to core.horse64.org.\033[0m"
	@echo "To test horsec right away in hacky Python mode, type:"
	@echo ""
	@echo "    tools/horsec_translated.py ...args..."
	@echo ""
	@echo "To build it all properly and get standalone binaries,"
	@echo "check the README.md file. But in short, use: make bootstrap"
bootstrap:
	$(MAKE) test-translator
test: test-translator
test-translator:
	@# Unit tests for bootstrap translator:
	@echo -e "\033[95;40mTest via bootstrap translator unit tests...\033[0m"
	python3 -m unittest discover tools 'test*.py'
	@echo "Regular unit tests done!"
	@# Regular test suite from here:
	@echo -e "\033[95;40mTesting the bootstrap translator with full test suite...\033[0m"
	tools/testfind_translated.py --tl-opt stdlib,. .
	@# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
