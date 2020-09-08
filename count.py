from miniprims import Model, Chunk, SlotID, EqualsPrim, NotEqualsPrim, CopyPrim
import random

model = Model()
m = model.modules['RT'].memory

m.append(Chunk.build('start-count', 'operator', 'count-fact', 'say',
                     condition=[NotEqualsPrim(SlotID('V', 1), None),
                                EqualsPrim(SlotID('WM', 1), None)],
                     action=[CopyPrim(SlotID('V', 1), SlotID('WM', 1)),
                             CopyPrim(SlotID('C', 1), SlotID('RT', 1)),
                             CopyPrim(SlotID('V', 1), SlotID('RT', 2)),
                             CopyPrim(SlotID('C', 2), SlotID('AC', 1)),
                             CopyPrim(SlotID('V', 1), SlotID('AC', 2))]))
m.append(Chunk.build('iterate', 'operator', 'count-fact', 'say',
                     condition=[EqualsPrim(SlotID('RT', 2), SlotID('WM', 1)),
                                NotEqualsPrim(SlotID('V',  2),
                                              SlotID('WM', 1))],
                     action=[CopyPrim(SlotID('RT', 3), SlotID('WM', 1)),
                             CopyPrim(SlotID('C',  1), SlotID('RT', 1)),
                             CopyPrim(SlotID('RT', 3), SlotID('RT', 2)),
                             CopyPrim(SlotID('C',  2), SlotID('AC', 1)),
                             CopyPrim(SlotID('RT', 3), SlotID('AC', 2))]))
m.append(Chunk.build('final', 'operator', 'say', 'stop',
                     condition=[EqualsPrim(SlotID('V', 2), SlotID('WM', 1))],
                     # FIXME: last action 'nil -> G1' removed
                     action=[CopyPrim(SlotID('C', 1), SlotID('AC', 1)),
                             CopyPrim(SlotID('C', 2), SlotID('AC', 2))]))

digits = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
          'nine', 'ten']
for i in range(1, len(digits)):
    m.append(Chunk.build(f'cf{i}', 'fact', 'count-fact', digits[i - 1],
                         digits[i]))

start = random.randint(0, 3)
end = start + 1 + random.randint(0, 3)
print("Counting from", digits[start], "to", digits[end])
model.modules['V'].buffer.slots = {1: digits[start], 2: digits[end]}

model.env.run()
print("done")
# issue reward
# trial end
