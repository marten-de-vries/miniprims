# Add numbers by counting
# The script assumes that the final action is "answer"
#

import miniprims


class Add(miniprims.Skill):
    def start_adding(self, zero, count_fact):
        WM[1] != None

        V[1] > WM[1]
        zero > WM[2]
        count_fact > RT[1]
        V[1] > RT[2]

    def increase_sum(self, count_fact):
        WM[1] == RT[2]
        WM[2] != V[2]

        RT[3] > WM[1]
        count_fact > RT[1]
        WM[2] > RT[2]

    def increase_count(self, count_fact):
        WM[2] == RT[2]
        WM[2] != V[2]

        RT[3] > WM[2]
        count_fact > RT[1]
        WM[1] > RT[2]

    def finish(self, answer):
        WM[2] == V[2]

        answer > AC[1]
        WM[1] > AC[2]


model = miniprims.Model()

digits = ["zero", "one", "two", "three", "four", "five", "six", "seven",
          "eight", "nine", "ten"]
for i in range(0, 10):
    model.add_dm(f"cf{i}", "count-fact", digits[i], digits[i + 1],
                 activation=3.0)
# model.add_dm('cf0', 'count-fact', 'zero', 'one', activation=3.0)
# model.add_dm('cf1', 'count-fact', 'one', 'two', activation=3.0)
# model.add_dm('cf2', 'count-fact', 'two', 'three', activation=3.0)
# model.add_dm('cf3', 'count-fact', 'three', 'four', activation=3.0)
# model.add_dm('cf4', 'count-fact', 'four', 'five', activation=3.0)
# model.add_dm('cf5', 'count-fact', 'five', 'six', activation=3.0)
# model.add_dm('cf6', 'count-fact', 'six', 'seven', activation=3.0)
# model.add_dm('cf7', 'count-fact', 'seven', 'eight', activation=3.0)
# model.add_dm('cf8', 'count-fact', 'eight', 'nine', activation=3.0)
# model.add_dm('cf9', 'count-fact', 'nine', 'ten', activation=3.0)

model.task('add', initial_skills={'add': Add()}, default_activation=1.0)


@model.script
def script():
    num1 = random(4) + 1
    num2 = random(4) + 1
    print("Adding", digits[num1], "and", digits[num2])

    model.screen(digits[num1],digits[num2])
    model.run_until_action("answer")
    model.issue_reward()
    model.trial_end()
