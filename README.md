flake8 miniprims/ count.py parse.py --max-complexity 5

python -m cProfile -o profile count.py
snakeviz profile

cloc miniprims/__init__.py miniprims/chunk.py miniprims/defaults.ini miniprims/modules.py miniprims/production.py miniprims/utils.py
