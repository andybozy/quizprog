**QuizProg** is a simple quiz program written in Python. It loads data from a pre-made JSON file.

# Usage
```
python3 quizprog.py [-h, --help] json_path
```
## Parameters
| Parameter | Description |
|--|--|
| `json_path` | Path to the JSON file which will be used to load quiz data. |
| `-d, --disablelog` | Disable logging. |
| `-h, --help` | Show help. |

# Valid Variables
- `title` (`string`) - The title of your quiz.
- `description` (`string`) - A description of your quiz. Will not show if not specified. *(optional)*
- `lives` (`int`) - The maximum amount of times a player can get a question incorrect. If not specified, the lives mechanic will be disabled. *(optional)*
- `randomize` (`bool`) - Set to `true` to randomize the order of questions. If not specified, uses default value. *(optional; default: `false`)*
- `showcount` (`bool`) - Set to `false` to hide the question count. If not specified, uses default value. *(optional; default: `true`)*
- `wrongmsg` (`list`) - Lists global incorrect answer messages (not to be confused with the `wrongmsg` dictionary for each individual question). If not specified or empty, this feature will be disabled. *(optional)*
- `questions` (`list`) - The questions of the quiz.
- - For each question (`dict`) in `questions`:
- - `question` (`string`) - The question.
- - `a`, `b`, `c`, `d` (`string`) - The 4 choices (A, B, C, D).
- - `wrongmsg` (`dict`) - Lists incorrect answer messages when a player chooses one.
- - - In `wrongmsg`:
- - - `a`, `b`, `c`, `d` (`string`) - Incorrect answer message when choosing an incorrect answer. The message for the correct answer will be ignored and is optional.
- - `correct` (`string`) - Can be either `a`, `b`, `c`, `d` or `all`. Specifies the correct answer. If set to `all`, all answers are correct.
- - `explanation` (`string`) - An explanation of the question. *(optional)*
- `fail` (`string`) - Fail message when running out of lives. If specified, must be used with the `lives` variable. If not specified, uses a generic fail message. *(optional)*
- `finish` (`string`) - Finish message when completing all the quiz questions.
