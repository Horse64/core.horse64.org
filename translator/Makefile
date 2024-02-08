
.PHONY: .test-translator ensure-hvm rebuild-hvm ensure-hvm-built

intro-message:
	@echo -e "\033[95;40mWelcome to core.horse64.org bootstrap.\033[0m"
	@echo "To bootstrap horsec, type:"
	@echo ""
	@echo "    make get-deps"
	@echo "    make bootstrap"
	@echo ""
	@echo "But make sure you got all the dependencies first."
	@echo "Check translator/translator-manual.md for dependencies,"
	@echo "as well as HVM's documentation. (The Horse64 VM.)"
bootstrap: ensure-hvm ensure-horp
	$(MAKE) ensure-cython-built ensure-hvm-built
	cd .. && translator/horsec.py compile src/compiler/main.h64
get-deps: ensure-hvm ensure-horp ensure-cython-built
ensure-cython-built:
	@cd .. && python3 ./translator/make_cython.py
rebuild-hvm:
	cd ../horse_modules/hvm.horse64.org/ && git reset --hard main && make veryclean && git pull && git submodule foreach --recursive git reset --hard && git submodule foreach --recursive git clean -xfd && git submodule update --init
	rm -rf ../horse_modules/hvm.horse64.org/output/*.so
	$(MAKE) ensure-hvm
reset-deps:
	cd .. && rm -rf ./horse_modules/
	cd .. && git submodule foreach --recursive git reset --hard && git submodule foreach --recursive git clean -xfd && git submodule update --init
	$(MAKE) ensure-hvm ensure-horp
ensure-hvm:
	@if [ ! -e ../horse_modules ]; then mkdir ../horse_modules; fi
	@if [ ! -e ../horse_modules/hvm.horse64.org ]; then git clone https://codeberg.org/Horse64/hvm.horse64.org ../horse_modules/hvm.horse64.org; fi
ensure-hvm-built:
	@if [ ! -e ../horse_modules/hvm.horse64.org/output/HVM-headless.so ]; then cd ../horse_modules/hvm.horse64.org/ && git submodule update --init && HORSERUN="python3 '$(PWD)/horsec_run.py'" $(MAKE) build-headless; fi
ensure-horp:
	@if [ ! -e ../horse_modules ]; then mkdir ../horse_modules; fi
	@if [ ! -e ../horse_modules/horp.horse64.org ]; then git clone https://codeberg.org/Horse64/core.horse64.org ../horse_modules/horp.horse64.org; fi
test:
	$(MAKE) test-translator
	$(MAKE) test-translated-horsec
test-translator:
	@# Unit tests for bootstrap translator:
	@echo -e "\033[95;40mTest via bootstrap translator unit tests...\033[0m"
	cd .. && python3 -m unittest discover translator/translator_modules/ 'test*.py'
	@echo "Regular unit tests done!"
	@# Regular test suite from here:
	@echo -e "\033[95;40mTesting the bootstrap translator with full test suite...\033[0m"
	cd .. && translator/testfind_translated.py --exclude-dir tests/ --exclude-dir src --tl-opt stdlib,. .
	@# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
test-translated-horsec:
	@# Component tests for translated horsec:
	@echo -e "\033[95;40mTest via translated horsec component tests...\033[0m"
	cd .. && python3 translator/run_tests_with_output_translated.py
	@# Done!
	@echo -e "\033[92;40mCompleted tests for translated horsec.\033[0m"

