
.PHONY: .test-translator

test-translator:
	@# Unit tests for bootstrap translator:
	@echo -e "\033[95;40mTest via bootstrap translator unit tests...\033[0m"
	python -m unittest discover tools 'test*.py'
	@echo "Regular unit tests done!"
	@# Regular test suite from here:
	@echo -e "\033[95;40mTesting the bootstrap translator with full test suite...\033[0m"
	@# This is a hack, but copy our own folder recursively into the tests:
	@echo "Copying folders in hacky ways..."
	rm -rf ./tests/basic-1/horse_modules/core.horse64.org/
	rm -rf ./tests/basic-2/horse_modules/core.horse64.org/
	rm -rf ./tests/args/horse_modules/core.horse64.org/
	rm -rf ./tests/rescue/horse_modules/core.horse64.org/
	rm -rf ./tests/inlinefunc/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	cp -R /tmp/h64-test-core-copy/ ./tests/rescue/horse_modules/core.horse64.org/
	cp -R /tmp/h64-test-core-copy/ ./tests/basic-1/horse_modules/core.horse64.org/
	cp -R /tmp/h64-test-core-copy/ ./tests/basic-2/horse_modules/core.horse64.org/
	cp -R /tmp/h64-test-core-copy/ ./tests/args/horse_modules/core.horse64.org/
	cp -R /tmp/h64-test-core-copy/ ./tests/inlinefunc/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	@# Then run the actual tests:
	tools/testfind_nobootstrap.py .
	@# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
