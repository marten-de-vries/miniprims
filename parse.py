from miniprims.loader import load

filename = 'count.prims'
model = load(filename)
# show resulting declarative memory
for chunk in model.modules['RT'].memory:
    print(chunk)
model.run()
