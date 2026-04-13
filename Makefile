.PHONY: test test-isolated

test:
	pytest spyne/test/ -x -q

test-isolated:
	@failed_files=""; \
	for f in $$(find spyne/test -name 'test_*.py' | sort); do \
		printf '\n=== %s ===\n' "$$f"; \
		if ! pytest $$f -x --tb=short -q 2>&1; then \
			failed_files="$$failed_files $$f"; \
		fi; \
	done; \
	echo ""; \
	if [ -z "$$failed_files" ]; then \
		echo "All files passed."; \
	else \
		echo "Failed files:"; \
		for f in $$failed_files; do echo "  $$f"; done; \
		exit 1; \
	fi
