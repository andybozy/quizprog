import os
import sys
import json
if os.name == 'nt': import msvcrt
else: import getch as msvcrt
import random
import keyboard
import requests
import tempfile
import traceback
from urllib import parse as urlparse

version = '1.0.4'

import argparse
parser = argparse.ArgumentParser(description = 'Loads a pre-made quiz from a JSON, either from the internet or locally.', epilog = 'QuizProg v{0}\n(c) 2022 GamingWithEvets Inc. All rights reserved.'.format(version), formatter_class = argparse.RawTextHelpFormatter, allow_abbrev = False)
parser.add_argument('path', metavar = 'json_path', help = 'path/URL to your JSON file')
parser.add_argument('-d', '--disable-log', action = 'store_true', help = 'disable logging')
args = parser.parse_args()

if not args.disable_log: logfile = open('quizprog.log', 'a', encoding = 'utf-8') 

def print_tag(string: str, function = 'main', error = False):
	if not args.disable_log:
		if error: logfile.write('\n' + function + ': ' + string + ' [!]')
		else: logfile.write('\n' + function + ': ' + string)

def abort():
	print_tag('aborting.\n\n')

if not args.disable_log: logfile.write('main: starting')
print_tag('quizprog v' + version)

is_url = urlparse.urlparse(args.path).scheme != ''


if is_url:
	print_tag('detected: URL')
	try:
		print_tag('downloading from: ' + args.path)
		response = requests.get(args.path)
		print_tag('got response: ' + str(response.status_code) + ' ' + response.reason)
		if response.status_code != 200:
			print_tag('expected status code 200 [!]')
			abort()
			parser.error(str(response.status_code) + ' ' + response.reason)
	except Exception:
		print_tag('internet connection error occurred [!]')
		abort()
		parser.error('error connecting to URL. maybe check your internet connection?')
	file = tempfile.TemporaryFile(mode = 'w+')
	file.write(response.text)
	file.seek(0)
else:
	print_tag('detected: local file')
	if not os.path.exists(args.path):
		print_tag('finding file "' + os.path.abspath(args.path) + '": not found [!]')
		abort()
		parser.error('invalid file path')
	else:
		print_tag('finding file "' + os.path.abspath(args.path) + '": found')
		path = args.path

try:
	if is_url: datafile = json.load(file)
	else: datafile = json.load(open(path, 'r', encoding = 'utf-8'))
except:
	print_tag('invalid JSON data [!]\n' + traceback.format_exc())
	abort()
	parser.error('invalid JSON data')

def clear():
	done = False
	while not done:
		try:
			if os.name == 'nt': os.system('cls')
			else: os.system('clear')
			done = True
		except:
			pass

def check_element(element, valtype = str):
	function = 'check_element'
	if element not in datafile:
		print_tag('checking element "' + element + '": not found', function, True)
		abort()
		parser.error('element "' + element + '" is required')
	else: print_tag('checking element "' + element + '": found', function)

	if not datafile[element]:
		print_tag('element "' + element + '" is blank/NoneType', function, True)
		abort()
		parser.error('element "' + element + '" cannot be blank or NoneType')

	if type(datafile[element]) is not valtype:
		print_tag('checking type of element "' + element + '": ' + type(datafile[element]).__name__, function, True)
		abort()
		parser.error('invalid str value in element "' + element + '"')
	else: print_tag('checking type of element "' + element + '": ' + type(datafile[element]).__name__, function)

def check_question_element(element, qid):
	function = 'check_question_element'
	if element not in datafile['questions'][qid]:
		print_tag('checking question element "' + element + '" in question ' + str(qid + 1) + ': not found', function, True)
		abort()
		parser.error('element "' + element + '" in question ' + str(qid + 1) + ' is required')
	else: print_tag('checking question element "' + element + '" in question ' + str(qid + 1) + ': found', function)

	if not datafile['questions'][qid][element]:
		print_tag('question element "' + element + '" in question ' + str(qid + 1) + ' is blank/NoneType', function, True)
		abort()
		parser.error('element "' + element + '" in question ' + str(qid + 1) + ' cannot be blank or NoneType', function)

	if type(datafile['questions'][qid][element]) is not str:
		print_tag('checking type of question element "' + element + '" in question ' + str(qid + 1) + '": ' + type(datafile['questions'][qid][element]).__name__, function, True)
		abort()
		parser.error('invalid str value in element "' + element + '" in question ' + str(qid + 1))
	else: print_tag('checking type of question element "' + element + '" in question ' + str(qid + 1) + '": ' + type(datafile['questions'][qid][element]).__name__, function)

def check_optional_element(element, valtype = str):
	function = 'check_optional_element'

	test1 = False
	test2 = False
	test3 = False
	if element not in datafile:
		print_tag('(test 1 failure) checking optional element "' + element + '": not found', function)
	else:
		print_tag('(test 1 success) checking optional element "' + element + '": found', function)
		test1 = True
		if type(datafile[element]) is not bool and not datafile[element]: print_tag('(test 2 failure) element "' + element + '" is blank/NoneType', function)
		elif type(datafile[element]) is bool:
			print_tag('test 2 skipped', function)
			test2 = True
		else:
			print_tag('(test 2 success) element "' + element + '" is not blank and not NoneType', function)
			test2 = True
		if type(datafile[element]) is valtype:
			print_tag('(test 3 success) checking type of optional element "' + element + '": ' + type(datafile[element]).__name__, function)
			test3 = True
		else: print_tag('(test 3 failure) checking type of optional element "' + element + '": ' + type(datafile[element]).__name__, function)

	if test1 and test2 and test3: return True
	else: return False

def check_question_optional_element(element, qid, valtype = str):
	function = 'check_question_optional_element'
	
	test1 = False
	test2 = False
	test3 = False

	if element not in datafile['questions'][qid]:
		print_tag('(test 1 failure) checking optional question element "' + element + '" in question ' + str(qid + 1) + ': not found', function)
	else:
		print_tag('(test 1 success) checking optional question element "' + element + '" in question ' + str(qid + 1) + ': found', function)
		test1 = True
		if not datafile['questions'][qid][element]: print_tag('(test 2 failure) question element "' + element + '" in question ' + str(qid + 1) + ' is blank/NoneType', function)
		else:
			print_tag('(test 2 success) question element "' + element + '" in question ' + str(qid + 1) + ' is not blank and not NoneType', function)
			test2 = True
		if type(datafile['questions'][qid][element]) is valtype:
			print_tag('(test 3 success) checking type of optional question element "' + element + '" in question ' + str(qid + 1) + '": ' + type(datafile['questions'][qid][element]).__name__, function)
			test3 = True
		else: print_tag('(test 3 failure) checking type of optional question element "' + element + '" in question ' + str(qid + 1) + '": ' + type(datafile['questions'][qid][element]).__name__, function)

	if test1 and test2 and test3: return True
	else: return False

check_element('title')
check_element('questions', list)
print_tag('got ' + str(len(datafile['questions'])) + ' questions')
if len(datafile['questions']) < 1:
	print_tag('question count is too low [!]')
	abort()
	parser.error('there must be at least one question in "questions"')
for i in range(len(datafile['questions'])):
	check_question_element('question', i)
	check_question_element('a', i)
	check_question_element('b', i)
	check_question_element('c', i)
	check_question_element('d', i)
	check_question_element('correct', i)

def load_quizzes():
	function = 'load_quizzes'

	print_tag('initializing lives', function)
	allow_lives = False
	lives = 0
	if check_optional_element('lives', int):
		lives = datafile['lives']
		print_tag(f'got {lives} lives', function)
		if lives >= 1: allow_lives = True
		else: print_tag('disabling lives', function)
	else: print_tag('disabling lives', function)

	print_tag('initializing global wrong messages', function)
	allow_wrong = False
	wrongmsg = []
	if check_optional_element('wrongmsg', list):
		wrongmsg = datafile['wrongmsg']
		print_tag(f'got {len(wrongmsg)} global wrong messages', function)
		if len(wrongmsg) >= 1: allow_wrong = True
		else: print_tag('disabling global wrong messages', function)
	else: print_tag('disabling global wrong messages', function)

	showcount = True
	if check_optional_element('showcount', bool):
		showcount = datafile['showcount']
		if not showcount: print_tag('question count will be hidden', function)
	else: print_tag('question count will be shown', function)

	rangelist = {}
	for i in range(len(datafile['questions'])):
		rangelist[i] = i

	randomize = False
	if check_optional_element('randomize', bool): randomize = datafile['randomize']
	if randomize:
		print_tag('shuffling question order', function)
		templist = list(rangelist.values())
		random.shuffle(templist)
		rangelist = dict(zip(rangelist, templist))

	for i in rangelist:
		if randomize: print_tag('initializing data for question {0} ({1})'.format(i + 1, rangelist[i] + 1), function)
		else: print_tag(f'initializing data for question {i + 1}', function)
		question_data = datafile['questions'][rangelist[i]]
		print_wrong = False
		answered = False

		print_tag('displaying question', function)
		while not answered:
			clear()
			if allow_lives:
				if lives < 1:
					print('OUT OF LIVES!\n')
					if check_optional_element('fail'): print(datafile['fail'] + '\n')
					else: print('Uh oh! You ran out of lives. But don\'t worry!\nJust be better next time. ;)')
					print('CORRECT ANSWER: [{0}] {1}\n'.format(question_data['correct'].upper(), question_data[question_data['correct']]))
					print('Press any key to return.')
					keyboard.wait('\n')
					input()
					print_tag('quiz exited (out of lives)', function); return
				else: print('LIVES: {0}'.format(lives))
			if showcount: print('QUESTION {0}/{1}\n'.format(i + 1, len(datafile['questions'])))
			else: print('QUESTION {0}\n'.format(i + 1))
			print(question_data['question'] + '\n')
			print('[A] ' + question_data['a'])
			print('[B] ' + question_data['b'])
			print('[C] ' + question_data['c'])
			print('[D] ' + question_data['d'] + '\n')
			print('[E] Quit\n')
			if print_wrong:
				if check_question_optional_element('wrongmsg', rangelist[i], dict) and choice in question_data['wrongmsg']:
					print(question_data['wrongmsg'][choice] + '\n')
				elif allow_wrong: print(random.choice(wrongmsg))
				else:
					if allow_lives: print('Choice ' + choice.upper() + ' is incorrect! You lost a life!\n')
					else: print('Choice ' + choice.upper() + ' is incorrect!\n')

			print('Press A, B, C, D or E on your keyboard to choose.')
			choice = msvcrt.getch().decode('utf-8')
			if choice in ['a', 'b', 'c', 'd']:
				print_tag('user chose ' + choice.upper(), function)
				if question_data['correct'] == 'all': answered = True
				elif choice == question_data['correct']:
					print_tag('' + choice.upper() + ' is a correct answer', function)
					answered = True
				else:
					print_tag('' + choice.upper() + ' is an incorrect answer', function)
					if allow_lives:
						lives -= 1
						print_tag('user lost 1 life. lives left: ' + str(lives), function)
					print_wrong = True
			elif choice == 'e':
				while True:
					clear()
					print('ARE YOU SURE?\n')
					print('Are you sure you want to quit the quiz?')
					print('You will lose all your progress.\n')
					print('[Y] Yes / [N] No\n')
					print('Press Y or N on your keyboard to choose.')
					inputt = msvcrt.getch().decode('utf-8')
					if inputt == 'y': print_tag('quiz exited (manual)', function); return
					elif inputt == 'n': break
					else: pass
		clear()
		print_tag('displaying correct answer screen', function)
		if allow_lives: print('LIVES: {0}'.format(lives))
		print('CORRECT!\n')
		if check_question_optional_element('explanation', i): print(question_data['explanation'] + '\n')
		print('Press Enter to continue.')
		keyboard.wait('\n')
		input()
	clear()
	print('IT\'S THE END OF THE QUIZ!\n')
	if check_optional_element('finish'): print(datafile['finish'] + '\n')
	print('Press Enter to return.')
	keyboard.wait('\n')
	input()
	print_tag('quiz exited (finished)', function)

print_tag('initializing quiz menu')
quitted = False
error = False
print_tag('displaying quiz menu')
while not quitted:
	try:
		clear()
		print(datafile['title'].upper())
		print('\nPowered by QuizProg v' + version + '\n')
		if check_optional_element('description'): print(datafile['description'])
		print('\n[1] Start')
		print('[2] Quit\n')

		print('Press 1 or 2 on your keyboard to choose.')
		choice = int(msvcrt.getch().decode('utf-8'))
		if choice == 2: quitted = True
		elif choice == 1: print_tag('user has selected start'); load_quizzes(); print_tag('displaying quiz menu')
		else: pass

	except ValueError:
		pass
	except KeyboardInterrupt:
		clear()
		print('Detected Ctrl+C hotkey.\n' + traceback.format_exc())
		print_tag('detected CTRL+C hotkey\n' + traceback.format_exc())
		error = True
		quitted = True
	except:
		clear()
		print('An error has occurred.\n' + traceback.format_exc())
		print_tag('an error occurred [!]\n' + traceback.format_exc())
		error = True
		quitted = True


if error: print_tag('')
else: print_tag('user has quitted')
if is_url: print_tag('closing temporary downloaded file'); file.close()
if not error: clear()
abort()
if not args.disable_log: logfile.close()
exit()