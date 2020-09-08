import astor

from miniprims.loader import load

filename = 'count.prims'
script, model = load(filename)
# stress test correctness by converting/compiling the AST:
print(astor.to_source(script))
compile(script, filename, "exec")
# show resulting declarative memory
for chunk in model.modules['RT'].memory:
    print(chunk)
