**QuizProg** is a simple quiz program written in Python. It loads data from a pre-made JSON file.  
QuizProg also comes with an editor that you can use if you're not tech-savvy enough to know about JSON.

Make sure to install all the listed modules in `requirements.txt` first, individually or with `pip install -r requirements.txt`.

As the newest version of wxPython, one of the required modules to run the editor, currently doesn't build on Python 3.10, you can use Python 3.9 or [install a snapshot build for Python 3.10](https://wxpython.org/Phoenix/snapshot-builds/wxPython-4.1.2a1.dev5434+7d45ee6a-cp310-cp310-win_amd64.whl). Then use `pip install <wheel filename>` to install.

# Usage
QuizProg: `python3 quizprog.py [-h, --help] [-e, --enable-log] [json_path]`  
Editor: `python3 editor.py [-h, --help] [json_path]`

## Parameters
| Parameter | Description |
|--|--|
| `json_path` | Path to the JSON file which will be used to load quiz data. |
| `-e, --enable-log` | Enable logging. Used for debugging. (not available in editor) |
| `-h, --help` | Show help. |

# JSON Structure
The JSON data must be a dictionary containing these variables (except for optional ones, as they are... well, optional).  
The variables and their types are as follows:
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
- - `wrongmsg` (`dict`) - Lists incorrect answer messages when a player chooses one (not to be confused with the global `wrongmsg` dictionary). If not specified or empty, this feature will be disabled. *(optional)*
- - - In `wrongmsg`:
- - - `a`, `b`, `c`, `d` (`string`) - Incorrect answer message when choosing an incorrect choice. *(optional)*
- - `correct` (`string`) - Can be either `a`, `b`, `c`, `d` or `all`. Specifies the correct choice. If set to `all`, all choices are correct.
- - `explanation` (`string`) - An explanation of the question. If not specified, the correct answer screen will be skipped. *(optional)*
- `fail` (`string`) - Fail message when running out of lives. Must be used with the `lives` variable. *(optional)*
- `finish` (`string`) - Finish message when completing all the quiz questions.
