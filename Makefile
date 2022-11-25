
.PHONY: .test-translator

intro-message:
	@echo -e "\033[95;40mWelcome to core.horse64.org.\033[0m"
	@echo "To test horsec right away in hacky Python mode, type:"
	@echo ""
	@echo "    make get-deps"
	@echo "    tools/horsec.py ...args..."
	@echo ""
	@echo "To build it all properly and get standalone binaries,"
	@echo "check the README.md file. But in short, use: make bootstrap"
bootstrap: ensure-hvm ensure-horp
	$(MAKE) test-translator
get-deps: ensure-hvm ensure-horp
ensure-hvm:
	@if [ ! -e ./horse_modules ]; then mkdir horse_modules; fi
	@if [ ! -e ./horse_modules/hvm.horse64.org ]; then git clone https://codeberg.org/Horse64/hvm.horse64.org ./horse_modules/hvm.horse64.org; fi
	@if [ ! -e ./horse_modules/hvm.horse64.org/HVM-headless.so ]; then cd ./horse_modules/hvm.horse64.org/ && git submodule update --init && $(MAKE) build-headless; fi
ensure-horp:
	@if [ ! -e ./horse_modules ]; then mkdir horse_modules; fi
	@if [ ! -e ./horse_modules/horp.horse64.org ]; then git clone https://codeberg.org/Horse64/core.horse64.org ./horse_modules/horp.horse64.org; fi
test: test-translator
test-translator:
	@# Unit tests for bootstrap translator:
	@echo -e "\033[95;40mTest via bootstrap translator unit tests...\033[0m"
	python3 -m unittest discover tools/translator_modules/ 'test*.py'
	@echo "Regular unit tests done!"
	@# Regular test suite from here:
	@echo -e "\033[95;40mTesting the bootstrap translator with full test suite...\033[0m"
	tools/testfind_translated.py --tl-opt stdlib,. .
	@# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
