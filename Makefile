# Task runner for the workspace. The build system is colcon; this only wraps the
# commands so that what runs locally is what runs in CI, spelled the same way.
#
# Run `make` or `make help` for the list.

SHELL := /bin/bash
.DEFAULT_GOAL := help

ROS_SETUP ?= /opt/ros/jazzy/setup.bash
BUILD_TYPE ?= Debug
PACKAGE ?= nav_utils
LCOV_IGNORE := mismatch,gcov,unused,empty,negative
BRANCH_COVERAGE := --rc branch_coverage=1

# Every colcon call needs the ROS environment; sourcing it per recipe keeps the
# targets usable from a plain shell.
ros = source $(ROS_SETUP) &&

.PHONY: help
help:  ## Show this list
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build:  ## Build the workspace
	$(ros) colcon build --event-handlers console_direct+ \
		--cmake-args -DCMAKE_BUILD_TYPE=$(BUILD_TYPE)

.PHONY: test
test:  ## Build and run the tests
	$(ros) colcon test --event-handlers console_direct+ --packages-select $(PACKAGE)
	$(ros) colcon test-result --verbose

.PHONY: coverage
coverage:  ## Build with gcov, run the tests, write coverage_html/
	$(ros) colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DCOVERAGE=ON
	$(ros) colcon test --packages-select $(PACKAGE) --ctest-args -R "^test_"
	lcov --capture --initial --directory build --output-file coverage.base \
		--ignore-errors $(LCOV_IGNORE) $(BRANCH_COVERAGE)
	lcov --capture --directory build --output-file coverage.run \
		--ignore-errors $(LCOV_IGNORE) $(BRANCH_COVERAGE)
	lcov --add-tracefile coverage.base --add-tracefile coverage.run \
		--output-file coverage.info --ignore-errors $(LCOV_IGNORE) $(BRANCH_COVERAGE)
	lcov --extract coverage.info "$(CURDIR)/src/*" \
		--output-file coverage.info --ignore-errors unused $(BRANCH_COVERAGE)
	lcov --remove coverage.info "*/test/*" \
		--output-file coverage.info --ignore-errors unused $(BRANCH_COVERAGE)
	lcov --list coverage.info $(BRANCH_COVERAGE)
	genhtml coverage.info --branch-coverage --legend --output-directory coverage_html \
		--ignore-errors inconsistent,corrupt
	@echo "report: file://$(CURDIR)/coverage_html/index.html"

.PHONY: lint
lint:  ## Run every pre-commit hook over the whole tree
	pre-commit run --all-files

.PHONY: hooks
hooks:  ## Install the commit, message and push hooks
	pre-commit install --install-hooks

.PHONY: tidy
tidy:  ## Run clang-tidy against the compilation database
	$(ros) colcon build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
	$(ros) run-clang-tidy -p build/$(PACKAGE) -quiet "$(CURDIR)/src/$(PACKAGE)/src/.*\.cpp"

.PHONY: asan
asan:  ## Build and test under AddressSanitizer and UBSan
	$(ros) colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DSANITIZE=address,undefined
	ASAN_OPTIONS=detect_leaks=1:strict_string_checks=1:detect_stack_use_after_return=1 \
	UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
		$(ros) colcon test --packages-select $(PACKAGE) --ctest-args -R "^test_"
	$(ros) colcon test-result --verbose

.PHONY: tsan
tsan:  ## Build and test under ThreadSanitizer
	@echo "note: needs vm.mmap_rnd_bits=28 on a 6.x kernel"
	$(ros) colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug -DSANITIZE=thread
	TSAN_OPTIONS=halt_on_error=1 \
		$(ros) colcon test --packages-select $(PACKAGE) --ctest-args -R "^test_"
	$(ros) colcon test-result --verbose

.PHONY: memcheck
memcheck:  ## Run the unit tests under valgrind
	$(ros) colcon build --cmake-args -DCMAKE_BUILD_TYPE=Debug
	@status=0; \
	for binary in build/$(PACKAGE)/test_*; do \
		[ -x "$$binary" ] || continue; \
		echo "== $$binary"; \
		valgrind --tool=memcheck --leak-check=full \
			--show-leak-kinds=definite,indirect --track-origins=yes \
			--error-exitcode=42 "$$binary" || status=$$?; \
	done; \
	exit $$status

.PHONY: fuzz
fuzz:  ## Build the libFuzzer targets (clang only) into build/fuzz
	cmake -S src/$(PACKAGE) -B build/fuzz -DFUZZING=ON \
		-DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Debug
	cmake --build build/fuzz

.PHONY: trend
trend:  ## Regenerate docs/coverage-trend.svg from the Codecov API
	scripts/coverage_trend.py --limit 20

.PHONY: requirements
requirements:  ## Regenerate the hash-pinned requirement files
	scripts/lock_requirements.py

.PHONY: act
act:  ## Run the lint workflow locally with act
	act -W .github/workflows/lint.yml

.PHONY: ci
ci: lint coverage tidy asan memcheck  ## Everything CI runs, in one go

.PHONY: clean
clean:  ## Remove the build, install and report directories
	rm -rf build install log coverage_html coverage.info coverage.base coverage.run
