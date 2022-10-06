
test-translator:
	# Unit tests for bootstrap translator:
	@echo -e "\033[95;40mTest via bootstrap translator unit tests...\033[0m"
	python -m unittest discover tools 'test*.py'
	# Regular test suite from here:
	@echo -e "\033[95;40mTesting the bootstrap translator with full test suite...\033[0m"
	# Wipe our horse_modules copies:
	rm -rf ./tests/basic-1/horse_modules/core.horse64.org/
	rm -rf ./tests/basic-2/horse_modules/core.horse64.org/
	rm -rf ./tests/args/horse_modules/core.horse64.org/
	rm -rf ./tests/rescue/horse_modules/core.horse64.org/
	rm -rf ./tests/inlinefunc/horse_modules/core.horse64.org/
	# rescue:
	rm -rf ./tests/rescue/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/rescue/horse_modules/core.horse64.org/
	tools/translator.py ./tests/rescue/main.h64
	# basic-1:
	rm -rf ./tests/basic-1/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/basic-1/horse_modules/core.horse64.org/
	tools/translator.py ./tests/basic-1/main.h64
	# basic-2:
	rm -rf ./tests/basic-2/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/basic-2/horse_modules/core.horse64.org/
	tools/translator.py ./tests/basic-2/main.h64
	# args:
	rm -rf ./tests/args/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/args/horse_modules/core.horse64.org/
	tools/translator.py ./tests/args/main.h64
	# inline func:
	rm -rf ./tests/inlinefunc/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/inlinefunc/horse_modules/core.horse64.org/
	tools/translator.py ./tests/inlinefunc/main.h64
	# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
