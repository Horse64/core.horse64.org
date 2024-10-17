#!/usr/bin/env python3
# Copyright (c) 2024, ellie/@ell1e & Horse64 authors (see AUTHORS.md).
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Alternatively, at your option, this file is offered under the Apache 2
# license, see accompanied LICENSE.md.

.PHONY: .test-translator ensure-hvm rebuild-hvm ensure-hvm-built

intro-message:
	@echo -e "\033[95;40mWelcome to core.horse64.org bootstrap.\033[0m"
	@echo "To bootstrap horsec and moosec, type:"
	@echo ""
	@echo "    make get-deps"
	@echo "    make bootstrap"
	@echo ""
	@echo "But make sure you got all the dependencies first."
	@echo "Check translator/README-translator.md for dependencies,"
	@echo "as well as HVM's documentation. (The Horse64 VM.)"
bootstrap: ensure-hvm ensure-horp
	$(MAKE) ensure-cython-built ensure-hvm-built
	cd .. && translator/horsec.py compile src/compiler/main.h64
get-deps: ensure-moose64 ensure-hvm ensure-horp ensure-cython-built
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
ensure-moose64:
	@if [ ! -e ../horse_modules ]; then mkdir ../horse_modules; fi
	@if [ ! -e ../horse_modules/m64.horse64.org ]; then git clone https://codeberg.org/Horse64/m64.horse64.org ../horse_modules/m64.horse64.org; fi
ensure-hvm:
	@if [ ! -e ../horse_modules ]; then mkdir ../horse_modules; fi
	@if [ ! -e ../horse_modules/hvm.horse64.org ]; then git clone https://codeberg.org/Horse64/hvm.horse64.org ../horse_modules/hvm.horse64.org; fi
ensure-hvm-built:
	@if [ ! -e ../horse_modules/hvm.horse64.org/output/HVM-headless.so ]; then cd ../horse_modules/hvm.horse64.org/ && git submodule update --init && HORP="python3 '$(PWD)/horp.py'" HORSERUN="python3 '$(PWD)/horsec_run.py'" $(MAKE) build-headless; fi
ensure-horp:
	@if [ ! -e ../horse_modules ]; then mkdir ../horse_modules; fi
	@if [ ! -e ../horse_modules/horp.horse64.org ]; then git clone https://codeberg.org/Horse64/horp.horse64.org ../horse_modules/horp.horse64.org; fi
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
	cd .. && translator/testfind_translated.py --exclude-dir tests/ --exclude-dir translator/ --tl-opt stdlib,. .
	@# Done!
	@echo -e "\033[92;40mCompleted tests for bootstrap translator.\033[0m"
test-translated-horsec:
	@# Component tests for translated horsec:
	@echo -e "\033[95;40mTest via translated horsec component tests...\033[0m"
	cd .. && python3 translator/run_tests_with_output_translated.py
	@# Done!
	@echo -e "\033[92;40mCompleted tests for translated horsec.\033[0m"

