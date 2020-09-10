# Add numbers by counting
# The script assumes that the final action is "answer"
#

import miniprims

import random


class Add(miniprims.Skill):
    def start_adding(zero, count_fact):
        WM[1] == None

        V[1] >> WM[1]
        zero >> WM[2]
        count_fact >> RT[1]
        V[1] >> RT[2]

    def increase_sum(count_fact):
        WM[1] == RT[2]
        WM[2] != V[2]

        RT[3] >> WM[1]
        count_fact >> RT[1]
        WM[2] >> RT[2]

    def increase_count(count_fact):
        WM[2] == RT[2]
        WM[2] != V[2]

        RT[3] >> WM[2]
        count_fact >> RT[1]
        WM[1] >> RT[2]

    def finish(answer):
        WM[2] == V[2]

        answer >> AC[1]
        WM[1] >> AC[2]


model = miniprims.Model('add')
model.config.override('default-activation', 1.0)

digits = ["zero", "one", "two", "three", "four", "five", "six", "seven",
          "eight", "nine", "ten"]
for i in range(0, 10):
    fact = model.chunk(f"cf{i}", "count_fact", digits[i], digits[i + 1],
                       activation=3.0)
    model.declarative.add_memory(fact)

model.register_skill('add', Add(model))
model.goal.focus(['add'])

num1 = random.randint(1, 5)
num2 = random.randint(1, 5)
print("Adding", digits[num1], "and", digits[num2])

model.visual.show(digits[num1],digits[num2])
model.action.interrupt_trigger = "answer"
model.schedule_steps_until_done()
model.env.run()
# model.issue_reward()
# model.trial_end()
