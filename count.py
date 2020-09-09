from miniprims import Model, SlotID, EqualsPRIM, NotEqualsPRIM, CopyPRIM
import random

model = Model()
model.name = 'count'
start_count = model.chunk('start-count', 'operator', 'count-fact', 'say',
                          condition=[NotEqualsPRIM(SlotID('V', 1), None),
                                     EqualsPRIM(SlotID('WM', 1), None)],
                          action=[CopyPRIM(SlotID('V', 1), SlotID('WM', 1)),
                                  CopyPRIM(SlotID('C', 1), SlotID('RT', 1)),
                                  CopyPRIM(SlotID('V', 1), SlotID('RT', 2)),
                                  CopyPRIM(SlotID('C', 2), SlotID('AC', 1)),
                                  CopyPRIM(SlotID('V', 1), SlotID('AC', 2))])
iterate = model.chunk('iterate', 'operator', 'count-fact', 'say',
                      condition=[EqualsPRIM(SlotID('RT', 2), SlotID('WM', 1)),
                                 NotEqualsPRIM(SlotID('V',  2),
                                               SlotID('WM', 1))],
                      action=[CopyPRIM(SlotID('RT', 3), SlotID('WM', 1)),
                              CopyPRIM(SlotID('C',  1), SlotID('RT', 1)),
                              CopyPRIM(SlotID('RT', 3), SlotID('RT', 2)),
                              CopyPRIM(SlotID('C',  2), SlotID('AC', 1)),
                              CopyPRIM(SlotID('RT', 3), SlotID('AC', 2))])
final = model.chunk('final', 'operator', 'say', 'stop',
                    condition=[EqualsPRIM(SlotID('V', 2), SlotID('WM', 1))],
                    # FIXME: last action 'nil -> G1' removed
                    action=[CopyPRIM(SlotID('C', 1), SlotID('AC', 1)),
                            CopyPRIM(SlotID('C', 2), SlotID('AC', 2))])

model.declarative.add_memory(start_count)
model.declarative.add_memory(iterate)
model.declarative.add_memory(final)

digits = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
          'nine', 'ten']
for i in range(1, len(digits)):
    fact = model.chunk(f'cf{i}', 'fact', 'count-fact', digits[i - 1],
                       digits[i])
    model.declarative.add_memory(fact)

start = random.randint(0, 3)
end = start + 1 + random.randint(0, 3)
print("Counting from", digits[start], "to", digits[end])

model.visual.show(digits[start], digits[end])
model.action.interrupt_trigger = ['say', 'stop']
model.action.register('say', 0.3, 0.1, 'uniform', 'Saying')

model.env.run()

print("done")
# issue reward
# trial end
