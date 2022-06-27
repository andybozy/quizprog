import os
import wx
import json
import time
if os.name == 'nt': import msvcrt
else: import getch as msvcrt
import keyboard
import requests
import tempfile
import traceback
from urllib import parse as urlparse

version = '1.1.0_04 - QuizProg v1.0.2_05'

app = wx.App(None)

import argparse
parser = argparse.ArgumentParser(description = 'QuizProg quiz editor.', epilog = 'QuizProg Editor v{0}\n(c) 2022 GamingWithEvets Inc. All rights reserved.'.format(version), formatter_class = argparse.RawTextHelpFormatter, allow_abbrev = False)
parser.add_argument('path', metavar = 'json_path', nargs = '?', help = 'path/URL to your JSON file (if you want to make changes to it)')
args = parser.parse_args()

if args.path != None:
	is_url = urlparse.urlparse(args.path).scheme != ''

	if is_url:
		try:
			response = requests.get(args.path)
			if response.status_code != 200: parser.error(str(response.status_code) + ' ' + response.reason)
		except Exception:
			parser.error('error connecting to URL. maybe check your internet connection?')
		file = tempfile.TemporaryFile(mode = 'w+')
		file.write(response.text)
		file.seek(0)
	else:
		if not os.path.exists(args.path): parser.error('invalid file path')
		else: path = args.path

	try:
		if is_url: datafile = json.load(file)
		else: datafile = json.load(open(path, 'r', encoding = 'utf-8'))
	except:
		parser.error('invalid JSON data')
else:
	is_url = False
	datafile = {'title': 'My Quiz', 'questions': [{'question': 'Question', 'a': 'Answer A', 'b': 'Answer B', 'c': 'Answer C', 'd': 'Answer D', 'correct': 'a'}]}

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
	if element not in datafile: parser.error('element "' + element + '" is required')
	if not datafile[element]: parser.error('element "' + element + '" cannot be blank or NoneType')
	if type(datafile[element]) is not valtype: parser.error('invalid str value in element "' + element + '"')

def check_question_element(element, qid):
	if element not in datafile['questions'][qid]: parser.error('element "' + element + '" in question ' + str(qid + 1) + ' is required')
	if not datafile['questions'][qid][element]: parser.error('element "' + element + '" in question ' + str(qid + 1) + ' cannot be blank or NoneType')
	if type(datafile['questions'][qid][element]) is not str: parser.error('invalid str value in element "' + element + '" in question ' + str(qid + 1))

def check_optional_element(element, valtype = str):
	test1 = False
	test2 = False
	test3 = False
	if element in datafile:
		test1 = True
		if not (type(datafile[element]) is not bool and not datafile[element]): test2 = True
		if type(datafile[element]) is valtype: test3 = True

	if test1 and test2 and test3: return True
	else: return False

def check_question_optional_element(element, qid, valtype = str):
	test1 = False
	test2 = False
	test3 = False

	if element in datafile['questions'][qid]:
		test1 = True
		if datafile['questions'][qid][element]: test2 = True
		if type(datafile['questions'][qid][element]) is valtype: test3 = True

	if test1 and test2 and test3: return True
	else: return False

check_element('title')
check_element('questions', list)
if len(datafile['questions']) < 1:
	('question count is too low [!]')
	parser.error('there must be at least one question in "questions"')
for i in range(len(datafile['questions'])):
	check_question_element('question', i)
	check_question_element('a', i)
	check_question_element('b', i)
	check_question_element('c', i)
	check_question_element('d', i)
	check_question_element('correct', i)

datafile_bak = dict(datafile)

displayed = False

def input_string(name, short, og = '', new = False):
	global modified
	clear()
	if new: print('Type your new ' + name + '. If blank, the ' + short + ' will be discarded.')
	else: print('Type your revised ' + name + '. If blank, the existing ' + short + ' will be deleted.')
	print('\nPress Enter to end a line.')
	print('To stop typing, make sure the current line you\'re on is blank,')
	if os.name == 'nt': print('then press CTRL+Z then Enter.\n')
	else: print('then press CTRL+D then Enter.\n')
	if not new and og: print('If you need to copy something from the old ' + short + ', here it is:\n' + og + '\n')
	textlist = []
	textlist_checked = []
	while True:
		try:
			content = input()
			textlist.append(content)
		except EOFError:
			for line in textlist:
				if line: textlist_checked.append(line)
			text = '\n'.join(textlist_checked)
			break
	if text != og: modified = True
	return text

def display_tut():
	clear()
	print(f'''WELCOME TO THE QUIZPROG EDITOR!

This editor helps you create QuizProg quizzes easier than ever.
As QuizProg uses JSON data, its creator, ME, has decided to make
an easy-to-use tool for creating these quizzes! No need to learn
JSON at all.

QuizProg Editor v{version}
(c) 2022 GamingWithEvets Inc.
		''')
	print('Press Enter to start creating your quiz.')
	keyboard.wait('\n')
	input()

def change_questions():
	global modified, modified_sym, savepath
	n = 0

	def change_question():
		global modified, modified_sym, savepath
		exited_question = False
		while not exited_question:
			try:
				if modified: modified_sym = '*'
				else: modified_sym = ''
				clear()
				if savepath or is_url: print(savepath + modified_sym + '\n')
				else: print('Unsaved quiz' + modified_sym + '\n')
				print(str(n + 1) + ' / ' + str(len(datafile['questions'])))
				print('\n[1] Question         ' + question_data['question'])
				print('[2] Answer A         ' + question_data['a'])
				print('[3] Answer B         ' + question_data['b'])
				print('[4] Answer C         ' + question_data['c'])
				print('[5] Answer D         ' + question_data['d'])
				print('[6] Correct answer   ' + question_data['correct'].upper())
				if check_question_optional_element('explanation', n): print('\n[7] Explanation      ' + question_data['explanation'])
				else: print('[7] Explanation      None')
				print('[8] Return')
				print('\nPress the number keys on your keyboard to change or toggle a setting.')
				choice = int(msvcrt.getch().decode('utf-8'))
				if choice == 8: exited_question = True
				elif choice == 1:
					text = input_string('question', 'question', question_data['question'])
					if text: question_data['question'] = text
				elif choice == 2:
					text = input_string('answer to choice A', 'answer', question_data['a'])
					if text: question_data['a'] = text
				elif choice == 3:
					text = input_string('answer to choice B', 'answer', question_data['b'])
					if text: question_data['b'] = text
				elif choice == 4:
					text = input_string('answer to choice C', 'answer', question_data['c'])
					if text: question_data['c'] = text
				elif choice == 5:
					text = input_string('answer to choice D', 'answer', question_data['d'])
					if text: question_data['d'] = text
				elif choice == 6:
					if question_data['correct'] == 'a': question_data['correct'] = 'b'
					elif question_data['correct'] == 'b': question_data['correct'] = 'c'
					elif question_data['correct'] == 'c': question_data['correct'] = 'd'
					elif question_data['correct'] == 'd': question_data['correct'] = 'a'
				elif choice == 7:
					if check_question_optional_element('explanation', n): text = input_string('question explanation', 'explanation', question_data['explanation'])
					else: text = input_string('question explanation', 'explanation', new = True)
					if text: question_data['explanation'] = text
			except ValueError:
				pass

	exited_questions = False
	while not exited_questions:
		try:
			if modified: modified_sym = '*'
			else: modified_sym = ''
			clear()
			if savepath or is_url: print(savepath + modified_sym + '\n')
			else: print('Unsaved quiz' + modified_sym + '\n')
			if n >= len(datafile['questions']): n = len(datafile['questions']) - 1
			print(str(n + 1) + ' / ' + str(len(datafile['questions'])))
			question_data = datafile['questions'][n]
			print('\n' + question_data['question'] + '\n')
			if question_data['correct'] == 'a': print('[A] ' + question_data['a'] + ' (correct)')
			else: print('[A] ' + question_data['a'])
			if question_data['correct'] == 'b': print('[B] ' + question_data['b'] + ' (correct)')
			else: print('[B] ' + question_data['b'])
			if question_data['correct'] == 'c': print('[C] ' + question_data['c'] + ' (correct)')
			else: print('[C] ' + question_data['c'])
			if question_data['correct'] == 'd': print('[D] ' + question_data['d'] + ' (correct)\n')
			else: print('[D] ' + question_data['d'] + '\n')
			if len(datafile['questions']) != 1:
				if n == 0: print('               [2] Next')
				elif n + 1 == len(datafile['questions']): print('[1] Previous')
				else: print('[1] Previous   [2] Next')
			print('[3] New        [4] Edit')
			if len(datafile['questions']) > 1: print('[5] Remove     [6] Return')
			else: print('[6] Return')
			print('\nPress the number keys on your keyboard to choose.')
			choice = int(msvcrt.getch().decode('utf-8'))
			if choice == 6: exited_questions = True
			elif choice == 1:
				if n != 0: n -= 1
			elif choice == 2:
				if n + 1 != len(datafile['questions']): n += 1
			elif choice == 3:
				datafile['questions'].append({'question': 'Question', 'a': 'Answer A', 'b': 'Answer B', 'c': 'Answer C', 'd': 'Answer D', 'correct': 'a'})
				modified = True
				n = len(datafile['questions']) - 1
			elif choice == 4: change_question()
			elif choice == 5:
				if len(datafile['questions']) > 1:
					while True:
						clear()
						print('Are you sure you want to remove this question?\n(Y: Yes / N: No)')
						key = msvcrt.getwche()
						if key == 'y':
							del datafile['questions'][n]
							modified = True
							break
						elif key == 'n':
							break
		except ValueError:
				pass


def change_settings():
	global modified, modified_sym, savepath

	def wrongmsgs():
		global modified, modified_sym, savepath
		exited_wrongmsgs = False
		n = 0
		while not exited_wrongmsgs:
			try:
				if modified: modified_sym = '*'
				else: modified_sym = ''
				clear()
				if savepath or is_url: print(savepath + modified_sym + '\n')
				else: print('Unsaved quiz' + modified_sym + '\n')
				if len(datafile['wrongmsg']) < 1:
					print('No global wrong messages!\n\n[3] New        [6] Return')
				else:
					if n >= len(datafile['wrongmsg']): n = len(datafile['wrongmsg']) - 1
					print(str(n + 1) + ' / ' + str(len(datafile['wrongmsg'])))
					print('\n' + datafile['wrongmsg'][n] + '\n')
					if len(datafile['wrongmsg']) != 1:
						if n == 0: print('               [2] Next')
						elif n + 1 == len(datafile['wrongmsg']): print('[1] Previous')
						else: print('[1] Previous   [2] Next')
					print('[3] New        [4] Edit')
					print('[5] Remove     [6] Return')
				print('\nPress the number keys on your keyboard to choose.')
				choice = int(msvcrt.getch().decode('utf-8'))
				if choice == 6: exited_wrongmsgs = True
				elif choice == 3:
					text = input_string('global wrong message', 'message', new = True) 
					if text:
						datafile['wrongmsg'].append(text)
						modified = True
						n = len(datafile['wrongmsg']) - 1
				if len(datafile['wrongmsg']) >= 1:
					if choice == 1:
						if n != 0: n -= 1
					elif choice == 2:
						if n + 1 != len(datafile['wrongmsg']): n += 1
					elif choice == 4:
						text = input_string('global wrong message', 'message', datafile['wrongmsg'][n])
						if text: datafile['wrongmsg'][n] = text
					elif choice == 5:
						while True:
							clear()
							print('Are you sure you want to remove this global wrong message?\n(Y: Yes / N: No)')
							key = msvcrt.getwche()
							if key == 'y':
								del datafile['wrongmsg'][n]
								modified = True
								break
							elif key == 'n':
								break
			except ValueError:
				pass

	exited_settings = False
	if not check_optional_element('lives', int): datafile['lives'] = 0
	if not check_optional_element('randomize', bool): datafile['randomize'] = False
	if not check_optional_element('showcount', bool): datafile['showcount'] = True
	if not check_optional_element('wrongmsg', list): datafile['wrongmsg'] = []
	if not check_optional_element('fail'): datafile['fail'] = ''
	if not check_optional_element('finish'): datafile['finish'] = ''

	if datafile['lives'] < 1: datafile['lives'] = 0

	while not exited_settings:
		try:
			if modified: modified_sym = '*'
			else: modified_sym = ''
			clear()
			if savepath or is_url: print(savepath + modified_sym + '\n')
			else: print('Unsaved quiz' + modified_sym + '\n')
			if datafile['lives'] < 1: print('[1] Lives                     OFF')
			else: print('[1] Lives                     ' + str(datafile['lives']))
			if datafile['randomize']: print('[2] Shuffle question order    ON')
			else: print('[2] Shuffle question order    OFF')
			if datafile['showcount']: print('[3] Show question count       ON')
			else: print('[3] Show question count       OFF')
			if datafile['wrongmsg']:
				print('[4] Global wrong messages     '  + str(len(datafile['wrongmsg'])) + ' messages')
			else: print('[4] Global wrong messages     OFF')
			if datafile['lives'] >= 1:
				if datafile['fail']:
					fail_lines = datafile['fail'].split('\n')
					print('[5] Out of lives message      '  + fail_lines[0])
					if len(fail_lines) >= 1:
						for i in range(1, len(fail_lines)): print('                              '  + fail_lines[i])
				else: print('[5] Out of lives message      OFF')
			else: print('[5] Out of lives message      Requires life setting')
			if datafile['wrongmsg']:
				win_lines = datafile['finish'].split('\n')
				print('[6] Win message               '  + win_lines[0])
				if len(win_lines) >= 1:
					for i in range(1, len(win_lines)): print('                              '  + win_lines[i])
			else: print('[6] Global wrong messages     OFF')
			print('[7] Return')

			print('\nPress the number keys on your keyboard to change or toggle a setting.')
			choice = int(msvcrt.getch().decode('utf-8'))
			if choice == 7: exited_settings = True
			elif choice == 1:
				clear()
				print('Enter the amount of lives you want to have.\nThe number of lives must be between 1 and 2147483647 and must not be a decimal number.\nIf 0 or lower, the lives setting will be disabled.\nIf blank or contains non-numeric characters,\nprevious life count will be used.\n')
				og = datafile['lives']
				try:
					life = int(input())
					if life < 1: datafile['lives'] = 0
					else: datafile['lives'] = life
					if datafile['lives'] != og: modified = True
				except ValueError:
					pass
			elif choice == 2: datafile['randomize'] = not datafile['randomize']; modified = True
			elif choice == 3: datafile['showcount'] = not datafile['showcount']; modified = True
			elif choice == 4: wrongmsgs()
			elif choice == 5:
				if datafile['fail']: text = input_string('out of lives message', 'message', datafile['fail'])
				else: text = input_string('out of lives message', 'message', new = True)
				if text: datafile['fail'] = text
			elif choice == 6:
				if datafile['finish']: text = input_string('win message', 'message', datafile['finish'])
				else: text = input_string('win message', 'message', new = True)
				if text: datafile['finish'] = text

		except ValueError:
			pass

def save_menu():
	global modified, modified_sym, savepath, allow_save, datafile, is_url
	exited_save = False
	savepath_tmp = ''
	message = 'Any save-related messages will appear here.'
	while not exited_save:
		try:
			if modified: modified_sym = '*'
			else: modified_sym = ''
			clear()
			if savepath or is_url: print(savepath + modified_sym)
			else: print('Unsaved quiz' + modified_sym)
			print('\n' + message + '\n')
			if allow_save: print('[1] Save')
			print('[2] Save as...')
			if modified: print('[3] Reload')
			print('[4] Return')
			message = ''
			print('\nPress the number keys on your keyboard to choose.')
			choice = int(msvcrt.getch().decode('utf-8'))
			if choice == 4: exited_save = True
			elif choice == 1:
				if allow_save:
					with open(savepath, 'w+') as f: f.write(json.dumps(datafile, indent = 4))
					message = 'Saved!'
					modified = False
			elif choice == 2:
				clear()
				dlg = wx.FileDialog(None, 'Where we savin\', boys?', wildcard = 'JSON Files (*.json)|*.json|All Files (*.*)|*.*||', style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
				if dlg.ShowModal() == wx.ID_OK: savepath_tmp = dlg.GetPath()
				if savepath_tmp:
					savepath = savepath_tmp
					try:
						with open(savepath, 'w+') as f: f.write(json.dumps(datafile, indent = 4))
						message = 'JSON file saved as: ' + savepath
						modified = False
						allow_save = True
						is_url = False
					except IOError as e:
						message = 'Can\'t save file: ' + e.strerror
			elif choice == 3:
				if modified:
					while True:
						clear()
						print('Are you sure you want to reload your quiz and lose\nyour changes made in the editor?\n(Y: Yes / N: No)')
						key = msvcrt.getwche()
						if key == 'y':
							datafile = dict(datafile_bak)
							modified = False
							message = 'Quiz reloaded.'
							break
						elif key == 'n':
							break
		except ValueError:
			pass

quitted = False
error = False
modified = False
modified_sym = ''
if args.path == None: savepath = ''
elif is_url: savepath = args.path
else: savepath = os.path.realpath(args.path)
allow_save = args.path != None and not is_url
while not quitted:
	try:
		if modified: modified_sym = '*'
		else: modified_sym = ''
		if args.path == None and not displayed: display_tut(); displayed = True
		clear()
		if savepath or is_url: print(savepath + modified_sym)
		else: print('Unsaved quiz' + modified_sym)
		print('\n' + datafile['title'])
		if check_optional_element('description'): print(datafile['description'])
		else: print('(no description provided)')
		print('\n[1] Rename your quiz')
		print('[2] Add, change or delete quiz description')
		print('[3] Change quiz questions')
		print('[4] Change quiz settings')
		print('\n[5] Save menu')
		print('[6] Exit')
		print('\nPress the number keys on your keyboard to choose.')
		choice = int(msvcrt.getch().decode('utf-8'))
		if choice == 6:
			if modified:
				while True:
					clear()
					print('Exit without saving? (Y: Yes / N: No)')
					key = msvcrt.getwche()
					if key == 'y': quitted = True; break
					elif key == 'n': break
			else: quitted = True
		elif choice == 1:
			text = input_string('quiz name', 'name', datafile['title'])
			if text: datafile['title'] = text
		elif choice == 2:
			if check_optional_element('description'): text = input_string('quiz description', 'description', datafile['description'])
			else: text = input_string('quiz description', 'description', new = True)
			if text: datafile['description'] = text
		elif choice == 3: change_questions()
		elif choice == 4: change_settings()
		elif choice == 5: save_menu()
		else: pass

	except ValueError:
		pass
	except KeyboardInterrupt:
		clear()
		print('Detected Ctrl+C hotkey.\n' + traceback.format_exc())
		error = True
		quitted = True
	except:
		clear()
		print('An error has occurred.\n' + traceback.format_exc())
		error = True
		quitted = True

if is_url: file.close()
if not error: clear()
exit()