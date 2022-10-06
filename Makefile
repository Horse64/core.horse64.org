
test-translator:
	@echo -e "\033[95;40mTesting the bootstrap translator...\033[0m"
	# wipe our horse_modules copies:
	rm -rf ./tests/basic-1/horse_modules/core.horse64.org/
	rm -rf ./tests/basic-2/horse_modules/core.horse64.org/
	rm -rf ./tests/args/horse_modules/core.horse64.org/
	rm -rf ./tests/rescue/horse_modules/core.horse64.org/
	rm -rf ./tests/inlinefunc/horse_modules/core.horse64.org/
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
	# rescue:
	rm -rf ./tests/rescue/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/rescue/horse_modules/core.horse64.org/
	tools/translator.py ./tests/rescue/main.h64
	# inline func:
	rm -rf ./tests/inlinefunc/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/inlinefunc/horse_modules/core.horse64.org/
	tools/translator.py ./tests/inlinefunc/main.h64
	# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
