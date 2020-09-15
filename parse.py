from miniprims.loader import load

filename = 'count.prims'
model = load(filename)
# show resulting declarative memory
for chunk in model.modules['RT'].memory.values():
    print(chunk)

steps = model.schedule_run(times=10)
# example of how the caller is in control over the event loop
while not steps.processed:
    stop = model.env.run(model.current_step)
