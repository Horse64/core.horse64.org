
test:
	rm -rf ./tests/basic-1/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/basic-1/horse_modules/core.horse64.org/
	tools/translator.py ./tests/basic-1/main.h64
	rm -rf ./tests/args/horse_modules/core.horse64.org/
	rm -rf /tmp/h64-test-core-copy/
	cp -R ./ /tmp/h64-test-core-copy/
	mv /tmp/h64-test-core-copy/ ./tests/args/horse_modules/core.horse64.org/
	tools/translator.py ./tests/args/main.h64
