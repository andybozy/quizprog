import os
import re
import wx
import sys
import json
if os.name == 'nt': import msvcrt
else: import getch as msvcrt
import random
import keyboard
import requests
import tempfile
import traceback
from datetime import datetime

version = '1.1.0'

app = wx.App(None)

import argparse
parser = argparse.ArgumentParser(description = 'Loads a pre-made quiz from a JSON, either from the internet or locally.', epilog = 'QuizProg v{}\n(c) 2022 GamingWithEvets Inc. All rights reserved.'.format(version), formatter_class = argparse.RawTextHelpFormatter, allow_abbrev = False)
parser.add_argument('path', metavar = 'json_path', nargs = '?', help = 'path/URL to your JSON file (skips the main menu)')
parser.add_argument('-e', '--enable-log', action = 'store_true', help = 'enable logging (for debugging)')
args = parser.parse_args()

if args.enable_log: logfile = open('quizprog.log', 'a', encoding = 'utf-8') 

def print_tag(string: str, function = 'main', error = False):
	if args.enable_log:
		if error: logfile.write('\n[' + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + '] ' + function + ': ' + string + ' [!]')
		else: logfile.write('\n[' + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + '] ' + function + ': ' + string)

def abort():
	print_tag('aborting.\n\n')

if args.enable_log: logfile.write('[' + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + '] main: starting')
print_tag('quizprog v' + version)

if args.path != None:
	is_url = bool(re.search('(?P<url>https?://[^\s]+)', args.path))

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
		else: datafile = json.load(open(path, encoding = 'utf-8'))
		loaded_quiz = True
	except:
		print_tag('invalid JSON data [!]\n' + traceback.format_exc())
		abort()
		parser.error('invalid JSON data')
else:
	is_url = False
	loaded_quiz = False
	datafile = {}

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

if loaded_quiz:
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
else: print_tag('quiz not loaded, skipping element checks')

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
		if randomize: print_tag('initializing data for question {} ({})'.format(i + 1, rangelist[i] + 1), function)
		else: print_tag(f'initializing data for question {i + 1}', function)
		question_data = datafile['questions'][rangelist[i]]
		print_wrong = False
		answered = False

		print_tag('displaying question', function)
		while not answered:
			clear()
			if allow_lives:
				if lives < 1:
					print('GAME OVER!\n')
					if check_optional_element('fail'): print(datafile['fail'] + '\n')
					print('Press any key to return.')
					keyboard.wait('\n')
					input()
					print_tag('quiz exited (game over)', function); return
				else: print('LIVES: {}'.format(lives))
			if showcount: print('QUESTION {}/{}\n'.format(i + 1, len(datafile['questions'])))
			else: print(f'QUESTION {i + 1}\n')
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
			choice = msvcrt.getwch().lower()
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
					inputt = msvcrt.getwch().lower()
					if inputt == 'y': print_tag('quiz exited (manual)', function); return
					elif inputt == 'n': break
					else: pass
		if check_question_optional_element('explanation', i):
			clear()
			print_tag('displaying correct answer screen', function)
			if allow_lives: print(f'LIVES: {lives}')
			print('CORRECT!\n')
			print(question_data['explanation'] + '\n')
			print('Press Enter to continue.')
			keyboard.wait('\n')
			input()
		else: print_tag('skipping correct answer screen', function)
	clear()
	print('CONGRATULATIONS!\n')
	if check_optional_element('finish'): print(datafile['finish'] + '\n')
	print('Press Enter to return.')
	keyboard.wait('\n')
	input()
	print_tag('quiz exited (finished)', function)

def about():
	print_tag('user has selected about menu')
	print_tag('displaying about menu')
	clear()
	print(f'''QUIZPROG - VERSION {version}

(c) 2022 GamingWithEvets Inc. All rights reserved.''')
	print('\nPress Enter to return.')
	keyboard.wait('\n')
	input()

def quit_quiz():
	function = 'quit_quiz'

	global is_url, loaded_quiz
	if is_url: print_tag('closing temporary downloaded file', function); file.close()
	print_tag('setting variables', function)
	is_url = False
	loaded_quiz = False
	print_tag('clearing old quiz data', function)
	datafile = {}

def openf():
	function = 'openf'

	global message, datafile, loaded_quiz
	path = ''

	clear()
	dlg = wx.FileDialog(None, 'JSON file please!', wildcard = 'JSON Files (*.json)|*.json|All Files (*.*)|*.*||', style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
	if dlg.ShowModal() == wx.ID_OK: path = dlg.GetPath()
	if path:
		print_tag('opening file "' + os.path.abspath(path) + '"', function)
		try:
			for i in range(1):
				try: datafile = json.load(open(path))
				except Exception as e:
					print_tag('invalid JSON data\n' + traceback.format_exc(), function)
					message = 'Invalid JSON data!'; break
				if not check_optional_element('title'): message = 'String variable "title" not found!'; break
				if not check_optional_element('questions', list): message = 'String variable "questions" not found!'; break
				if len(datafile['questions']) < 1: message = 'There must be at least one question in the "questions" list!'; break
				success = False
				for i in range(len(datafile['questions'])):
					if not check_question_optional_element('question', i): message = 'String variable "question" not found in question ' + str(i+1) + '!'; break
					if not check_question_optional_element('a', i): message = 'String variable "a" not found in question ' + str(i+1) + '!'; break
					if not check_question_optional_element('b', i): message = 'String variable "b" not found in question ' + str(i+1) + '!'; break
					if not check_question_optional_element('c', i): message = 'String variable "c" not found in question ' + str(i+1) + '!'; break
					if not check_question_optional_element('d', i): message = 'String variable "d" not found in question ' + str(i+1) + '!'; break
					if not check_question_optional_element('correct', i): message = 'String variable "correct" not found in question ' + str(i+1) + '!'; break
					success = True
				if not success: break
				message = ''
				loaded_quiz = True
				is_url = False
			if not success: print_tag('quiz loading cancelled', function)
		except IOError as e:
			message = 'Can\'t open file: ' + e.strerror
			print_tag('IOError occurred: ' + e.strerror, function)
	else: print_tag('quiz opening cancelled', function)

print_tag('initializing variables')
quitted = False
error = False
message = 'Welcome to QuizProg! Any errors while opening a quiz will be displayed here.'
while not quitted:
	try:
		clear()
		if loaded_quiz:
			print_tag('displaying quiz menu')
			print(datafile['title'].upper())
			print('\nPowered by QuizProg v' + version + '\n')
			if check_optional_element('description'): print(datafile['description'])
			print('\n[1] Start quiz\n')
			print('[2] Open another quiz')
			print('[3] Quit quiz\n')
			print('[4] About QuizProg')
			print('[5] Quit QuizProg\n')

			print('Press the number keys on your keyboard to choose.')
			choice = int(msvcrt.getwch())
			if choice == 5: quitted = True
			elif choice == 1: print_tag('user has selected start'); load_quizzes(); print_tag('displaying quiz menu')
			elif choice == 2:
				while True:
					clear()
					print('To open another quiz, the current quiz must be quitted first.\nDo you want to continue? (Y: Yes / N: No)')
					key = msvcrt.getwch().lower()
					if key == 'y': print_tag('user has selected "open quiz"'); quit_quiz(); openf(); break
					elif key == 'n': break
			elif choice == 3:
				while True:
					clear()
					print('Are you sure you want to quit this quiz?\n(Y: Yes / N: No)')
					key = msvcrt.getwch().lower()
					if key == 'y': print_tag('user has quitted quiz'); quit_quiz()
					elif key == 'n': break
			elif choice == 4: about()
			else: pass
		else:
			print_tag('displaying quizprog menu')
			print('QUIZPROG LOADER\n')
			print(message + '\n')
			print('[1] Open quiz')
			print('[2] About QuizProg')
			print('[3] Quit\n')

			message = ''
			print('Press the number keys on your keyboard to choose.')
			choice = int(msvcrt.getwch())
			if choice == 3: quitted = True
			elif choice == 1: print_tag('user has selected "open quiz"'); openf()
			elif choice == 2: about()
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
else: print_tag('user has quitted quizprog')
if is_url: print_tag('closing temporary downloaded file'); file.close()
if not error: clear()
abort()
if args.enable_log: logfile.close()
sys.exit()