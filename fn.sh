git rm -r --cached __pycache__ engine/__pycache__ tests/__pycache__
git rm --cached up.sh
printf '\nup.sh\n' >> .gitignore
git mv gen_test_key.py tests/gen_test_key.py
