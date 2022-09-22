import os
import re
import sys
import copy
import json
import time
import ctypes
import tempfile
import traceback

version = '1.4.3'
quizprog_version = '1.1.8'


import argparse
parser = argparse.ArgumentParser(description = 'QuizProg quiz editor.', epilog = 'QuizProg Editor v{} - QuizProg v{}\n(c) 2022 GamingWithEvets Inc. All rights reserved.'.format(version, quizprog_version), formatter_class = argparse.RawTextHelpFormatter, allow_abbrev = False)
parser.add_argument('path', metavar = 'json_path', nargs = '?', help = 'path/URL to your JSON file (if you want to make changes to it)')
parser.add_argument('-n', '--no-tk', action = 'store_true', help = 'don\'t use Tkinter')
args = parser.parse_args()

if not args.no_tk:
	try:
		from tkinter import Tk
		from tkinter.filedialog import askopenfilename, asksaveasfile
	except ImportError: parser.error('"tkinter" module not found.\nto use QuizProg w/o Tkinter, use the -n / --no-tk option.'); sys.exit()
	tk = Tk()
	tk.withdraw()

if os.name == 'nt': import msvcrt
else:
	try:
		import getch
		class fake_getwch(object):
			def __init__(self, func): self.getwch = func
		msvcrt = fake_getwch(getch.getch)
	except ImportError: parser.error('"getch" module not found'); sys.exit()
try: import keyboard
except ImportError:
	if args.no_tk: parser.error('"keyboard" module not found\nplease run w/o the -n / --no-tk option\nif you don\'t want to install this module.'); sys.exit()
try:
	keyboard.press_and_release('esc')
	keyboard.write('\n')
	input()
except Exception:
	if args.no_tk: parser.error('"keyboard" module test failed\nplease run w/o the -n / --no-tk option!'); sys.exit()
try: import requests
except ImportError: parser.error('"requests" module not found'); sys.exit()

if args.path != None:
	is_url = bool(re.search('(?P<url>https?://[^\s]+)', args.path))

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
		else: datafile = json.load(open(path, encoding = 'utf-8'))
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
if len(datafile['questions']) < 1: parser.error('there must be at least one question in "questions"')
for i in range(len(datafile['questions'])):
	check_question_element('question', i)
	check_question_element('a', i)
	check_question_element('b', i)
	check_question_element('c', i)
	check_question_element('d', i)
	check_question_element('correct', i)

def create_backup():
	global datafile, datafile_bak
	datafile_bak = datafile.copy()
	datafile_bak['questions'] = copy.deepcopy(datafile['questions'])

create_backup()

def input_string(name, short, og = '', new = False, allow_blank = False, newline = True):
	global modified
	clear()
	print(header)
	if new: print('Type your new ' + name + '. If blank, the ' + short + ' will be discarded.')
	elif allow_blank: print('Type your revised ' + name + '. If blank, the existing ' + short + ' will be deleted.')
	else: print('Type your revised ' + name + '. If blank, the existing ' + short + ' will be kept.')
	if newline:
		print('\nPress Enter to end a line.\nTo stop typing, make sure the current line you\'re on is blank,')
		if os.name == 'nt': print('then press CTRL+Z then Enter.\n')
		else: print('then press CTRL+D then Enter.\n')
	else: print('Press Enter to stop typing.\n')
	if not new and og: print('If you need to copy something from the old ' + short + ', here it is:\n' + og + '\n')
	print('-----\n')
	textlist = []
	textlist_checked = []
	if newline:
		while True:
			try:
				content = input()
				textlist.append(content)
			except EOFError:
				for line in textlist:
					if line and not line.isspace(): textlist_checked.append(line)
				text = '\n'.join(textlist_checked)
				break
	else:
		try:
			text = input()
		except EOFError: return og
	if text and text != og: modified = True
	elif allow_blank: modified = True
	return text

def change_questions():
	global modified, modified_sym, savepath
	n = 0

	def change_question():
		global modified, modified_sym, savepath

		def change_wrongmsg():
			global modified, modified_sym, savepath
			exited_wrongmsg = False
			if not check_question_optional_element('wrongmsg', n, dict): question_data['wrongmsg'] = {}
			m = 'a'
			while not exited_wrongmsg:
				try:
					if modified: modified_sym = '*'
					else: modified_sym = ''
					set_title()
					clear()
					print(header)
					available_choices = ['a', 'b', 'c', 'd']
					for choice in question_data['wrongmsg']:
						if choice in available_choices: available_choices.remove(choice)
					if len(question_data['wrongmsg']) < 1:
						print('No wrong messages! - 4/4 available choice letters')
						print('\n\n[3] New\n')
						print('               [8] Return')
					else:
						while True:
							if m in question_data['wrongmsg']: break
							else:
								if m == 'a': m = 'b'
								elif m == 'b': m = 'c'
								elif m == 'c': m = 'd'
								elif m == 'd': m = 'a'
						print('CHOICE {} - {}/4 available choice letters'.format(m.upper(), len(available_choices)))
						print('\n' + question_data['wrongmsg'][m] + '\n')
						if len(question_data['wrongmsg']) != 1:
							if (m == 'c' and 'b' not in question_data['wrongmsg'] and 'a' not in question_data['wrongmsg']) \
or (n == 'b' and 'a' not in question_data['wrongmsg']) or m == 'a': print('               [2] Next')
							elif (m == 'b' and 'c' not in question_data['wrongmsg'] and 'd' not in question_data['wrongmsg']) \
or (n == 'c' and 'd' not in question_data['wrongmsg']) or m == 'd': print('[1] Previous')
							else: print('[1] Previous   [2] Next')
						else: print()
						if len(question_data['wrongmsg']) == 4:
							print('               [4] Edit')
							print('               [6] Move')
							print('[7] Remove     [8] Return')
						else:
							print('[3] New        [4] Edit')
							print('[5] Duplicate  [6] Move')
							print('[7] Remove     [8] Return')
					print('\nPress the number keys on your keyboard to choose.')
					choice = int(msvcrt.getwch())
					if choice == 8: exited_wrongmsg = True
					if choice == 1:
						if m == 'b' and 'a' in question_data['wrongmsg']: m = 'a'
						elif m == 'c':
							if 'b' not in question_data['wrongmsg']: m = 'a'
							else: m = 'b'
						elif m == 'd':
							if 'c' not in question_data['wrongmsg']:
								if 'b' not in question_data['wrongmsg']: m = 'a'
								else: m = 'b'
							else: m = 'c'
					elif choice == 2:
						if m == 'a':
							if 'b' not in question_data['wrongmsg']:
								if 'c' not in question_data['wrongmsg']: m = 'd'
								else: m = 'c'
							else: m = 'b'
						elif m == 'b':
							if 'c' not in question_data['wrongmsg']: m = 'd'
							else: m = 'c'
						elif m == 'c' and 'd' in question_data['wrongmsg']: m = 'd'
					elif choice == 3:
						if len(question_data['wrongmsg']) < 4:
							l = len(available_choices)
							if l > 0:
								if l > 1:
									while True:
										clear()
										print(f'{header}\nWhich choice do you want this wrong message for?')
										if l == 4: print('(A / B / C / D - E: Cancel)')
										elif l == 3: print('({} / {} / {} - E: Cancel)'.format(available_choices[0].upper(), available_choices[1].upper(), available_choices[2].upper()))
										elif l == 2: print('({} / {} - E: Cancel)'.format(available_choices[0].upper(), available_choices[1].upper()))
										key = msvcrt.getwch().lower()
										if key in available_choices:
											choice = key
											break
										elif key == 'e': choice = ''; break
								else: choice = available_choices[0]
								if choice:
									text = input_string('wrong message for choice ' + choice.upper(), 'message', new = True)
									if text:
										question_data['wrongmsg'][choice] = text
										modified = True
										m = choice
					if len(question_data['wrongmsg']) >= 1:
						if choice == 4:
							text = input_string('wrong message for choice ' + m, 'message', question_data['wrongmsg'][m])
							if text: question_data['wrongmsg'][m] = text
						elif choice == 5:
							if len(question_data['wrongmsg']) < 4:
								l = len(available_choices)
								if l > 0:
									if l > 1:
										while True:
											clear()
											print(f'{header}\nCopy this wrong message to which choice letter?')
											if l == 4: print('(A / B / C / D - E: Cancel)')
											elif l == 3: print('({} / {} / {} - E: Cancel)'.format(available_choices[0].upper(), available_choices[1].upper(), available_choices[2].upper()))
											elif l == 2: print('({} / {} - E: Cancel)'.format(available_choices[0].upper(), available_choices[1].upper()))
											key = msvcrt.getwch().lower()
											if key in available_choices:
												choice = key
												break
											elif key == 'e': choice = ''; break
									else: choice = available_choices[0]
									if choice:
										question_data['wrongmsg'][choice] = question_data['wrongmsg'][m]
										modified = True
										m = choice
						elif choice == 6:
							while True:
								clear()
								print(f'{header}\nWhat\'ll be the wrong message\'s new choice letter?')
								if m == 'a': print('(B / C / D - E: Cancel)')
								elif m == 'b': print('(A / C / D - E: Cancel)')
								elif m == 'c': print('(A / B / D - E: Cancel)')
								elif m == 'd': print('(A / B / C - E: Cancel)')
								choice = msvcrt.getwch().lower()
								if choice != m:
									if choice in ['a', 'b', 'c', 'd']:
										old_m = ''
										if choice in question_data['wrongmsg']: old_m = question_data['wrongmsg'][n]
										question_data['wrongmsg'][choice] = question_data['wrongmsg'].pop(n)
										if old_m: question_data['wrongmsg'][m] = old_m
										modified = True
										m = choice
										break
									elif choice == 'e': break
						elif choice == 7:
							while True:
								clear()
								print(f'{header}\nAre you sure you want to remove this wrong message?\n(Y: Yes / N: No)')
								key = msvcrt.getwch().lower()
								if key == 'y':
									del question_data['wrongmsg'][m]
									modified = True
									break
								elif key == 'n':
									break
				except ValueError:
					pass
			if len(question_data['wrongmsg']) < 1: del question_data['wrongmsg']

		exited_question = False
		while not exited_question:
			try:
				if modified: modified_sym = '*'
				else: modified_sym = ''
				set_title()

				if not check_question_optional_element('explanation', n): question_data['explanation'] = ''

				question_split = question_data['question'].split('\n')
				a_split = question_data['a'].split('\n')
				b_split = question_data['b'].split('\n')
				c_split = question_data['c'].split('\n')
				d_split = question_data['d'].split('\n')
				explanation_split = question_data['explanation'].split('\n')

				clear()
				print(header)
				print(str(n + 1) + ' / ' + str(len(datafile['questions'])))
				print('\n[1] Question         ' + question_split[0])
				if len(question_split) > 1:
					for line in range(1, len(question_split)): print('                     ' + question_split[line])
				print('[2] Answer A         ' + a_split[0])
				if len(a_split) > 1:
					for line in range(1, len(a_split)): print('                     ' + a_split[line])
				print('[3] Answer B         ' + b_split[0])
				if len(b_split) > 1:
					for line in range(1, len(b_split)): print('                     ' + b_split[line])
				print('[4] Answer C         ' + c_split[0])
				if len(c_split) > 1:
					for line in range(1, len(c_split)): print('                     ' + c_split[line])
				print('[5] Answer D         ' + d_split[0])
				if len(d_split) > 1:
					for line in range(1, len(d_split)): print('                     ' + d_split[line])
				print('[6] Wrong messages')
				if question_data['correct'] == 'all': print('[7] Correct answer   All')
				else: print('[7] Correct answer   ' + question_data['correct'].upper())
				if check_question_optional_element('explanation', n):
					print('[8] Explanation      ' + explanation_split[0])
					if len(explanation_split) > 1:
						for line in range(1, len(explanation_split)): print('                     ' + explanation_split[line])
				else: print('[8] Explanation      None')
				print('[9] Return')
				print('\nPress the number keys on your keyboard to change or toggle a setting.')
				choice = int(msvcrt.getwch())
				if choice == 9: exited_question = True
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
				elif choice == 6: change_wrongmsg()
				elif choice == 7:
					if question_data['correct'] == 'a': question_data['correct'] = 'b'
					elif question_data['correct'] == 'b': question_data['correct'] = 'c'
					elif question_data['correct'] == 'c': question_data['correct'] = 'd'
					elif question_data['correct'] == 'd': question_data['correct'] = 'all'
					elif question_data['correct'] == 'all': question_data['correct'] = 'a'
				elif choice == 8:
					if check_question_optional_element('explanation', n):
						text = input_string('question explanation', 'explanation', question_data['explanation'], allow_blank = True)
						question_data['explanation'] = text
					else:
						text = input_string('question explanation', 'explanation', new = True)
						if text: question_data['explanation'] = text
			except ValueError:
				pass
		if len(question_data['explanation']) < 1: del question_data['explanation']

	exited_questions = False
	while not exited_questions:
		try:
			if modified: modified_sym = '*'
			else: modified_sym = ''
			set_title()

			if n >= len(datafile['questions']): n = len(datafile['questions']) - 1
			
			question_data = datafile['questions'][n]
			a_split = question_data['a'].split('\n')
			b_split = question_data['b'].split('\n')
			c_split = question_data['c'].split('\n')
			d_split = question_data['d'].split('\n')

			clear()
			print(header)
			if n >= len(datafile['questions']): n = len(datafile['questions']) - 1
			print(str(n + 1) + ' / ' + str(len(datafile['questions'])))
			print('\n' + question_data['question'] + '\n')
			if question_data['correct'] == 'a' or question_data['correct'] == 'all':
				if len(a_split) > 1:
					print('[A] ' + a_split[0])
					for line in range(1, len(a_split) - 1): print('    ' + a_split[line])
					print('    ' + a_split[-1] + ' (correct)')
				else: print('[A] ' + question_data['a'] + ' (correct)')
			else:
				if len(a_split) > 1:
					print('[A] ' + a_split[0])
					for line in range(1, len(a_split)): print('    ' + a_split[line])
				else: print('[A] ' + question_data['a'])
			if question_data['correct'] == 'b' or question_data['correct'] == 'all':
				if len(b_split) > 1:
					print('[B] ' + b_split[0])
					for line in range(1, len(b_split) - 1): print('    ' + b_split[line])
					print('    ' + b_split[-1] + ' (correct)')
				else: print('[B] ' + question_data['b'] + ' (correct)')
			else:
				if len(b_split) > 1:
					print('[B] ' + b_split[0])
					for line in range(1, len(b_split)): print('    ' + b_split[line])
				else: print('[B] ' + question_data['b'])
			if question_data['correct'] == 'c' or question_data['correct'] == 'all':
				if len(c_split) > 1:
					print('[C] ' + c_split[0])
					for line in range(1, len(c_split) - 1): print('    ' + c_split[line])
					print('    ' + c_split[-1] + ' (correct)')
				else: print('[C] ' + question_data['c'] + ' (correct)')
			else:
				if len(c_split) > 1:
					print('[C] ' + c_split[0])
					for line in range(1, len(c_split)): print('    ' + c_split[line])
				else: print('[C] ' + question_data['c'])
			if question_data['correct'] == 'd' or question_data['correct'] == 'all':
				if len(d_split) > 1:
					print('[D] ' + d_split[0])
					for line in range(1, len(d_split) - 1): print('    ' + d_split[line])
					print('    ' + d_split[-1] + ' (correct)\n')
				else: print('[D] ' + question_data['d'] + ' (correct)\n')
			else:
				if len(d_split) > 1:
					print('[D] ' + d_split[0])
					for line in range(1, len(d_split) - 1): print('    ' + d_split[line])
					print('    ' + d_split[-1] + '\n')
				else: print('[D] ' + question_data['d'] + '\n')
			if len(datafile['questions']) != 1:
				if n == 0: print('               [2] Next')
				elif n + 1 == len(datafile['questions']): print('[1] Previous')
				else: print('[1] Previous   [2] Next')
			else: print()
			print('[3] New        [4] Edit')
			if len(datafile['questions']) > 1:
				print('[5] Duplicate  [6] Move')
				print('[7] Remove     [8] Return')
			else:
				print('[5] Duplicate  [6] Move')
				print('               [8] Return')
			print('\nPress the number keys on your keyboard to choose.')
			choice = int(msvcrt.getwch())
			if choice == 8: exited_questions = True
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
				datafile['questions'].append(datafile['questions'][n])
				modified = True
				n = len(datafile['questions']) - 1
			elif choice == 6:
				clear()
				print(f'{header}\nInput the question\'s new slot number.\nThe slot number must be between 1 and ' + str(len(datafile['questions'])) + '\nand must not be ' + str(n + 1) + '.\nOr else, the move operation will be cancelled.\nIf blank or contains non-numeric characters,\nprevious slot number will be used.\n')
				try:
					slot = int(input('-----\n\nNew slot number:'))
					if slot >= 1 and slot <= len(datafile['questions']) and slot != n + 1:
						datafile['questions'].insert(slot - 1, datafile['questions'].pop(n))
						if slot != n + 1: modified = True
						n = slot - 1
				except ValueError:
					pass
			elif choice == 7:
				if len(datafile['questions']) > 1:
					while True:
						clear()
						print(f'{header}\nAre you sure you want to remove this question?\n(Y: Yes / N: No)')
						key = msvcrt.getwch().lower()
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
				set_title()
				clear()
				print(header)
				if len(datafile['wrongmsg']) < 1:
					print('No global wrong messages!')
					print('\n\n[3] New\n')
					print('               [8] Return')
				else:
					if n >= len(datafile['wrongmsg']): n = len(datafile['wrongmsg']) - 1
					print(str(n + 1) + ' / ' + str(len(datafile['wrongmsg'])))
					print('\n' + datafile['wrongmsg'][n] + '\n')
					if len(datafile['wrongmsg']) != 1:
						if n == 0: print('               [2] Next')
						elif n + 1 == len(datafile['wrongmsg']): print('[1] Previous')
						else: print('[1] Previous   [2] Next')
					else: print()
					print('[3] New        [4] Edit')
					print('[5] Duplicate  [6] Move')
					print('[7] Remove     [8] Return')
				print('\nPress the number keys on your keyboard to choose.')
				choice = int(msvcrt.getwch())
				if choice == 8: exited_wrongmsgs = True
				elif choice == 1:
					if n != 0: n -= 1
				elif choice == 2:
					if n + 1 != len(datafile['wrongmsg']): n += 1
				elif choice == 3:
					text = input_string('global wrong message', 'message', new = True) 
					if text:
						datafile['wrongmsg'].append(text)
						modified = True
						n = len(datafile['wrongmsg']) - 1
				if len(datafile['wrongmsg']) >= 1:
					if choice == 4:
						text = input_string('global wrong message', 'message', datafile['wrongmsg'][n])
						if text: datafile['wrongmsg'][n] = text
					elif choice == 5:
						datafile['wrongmsg'].append(datafile['wrongmsg'][n])
						modified = True
						n = len(datafile['wrongmsg']) - 1
					elif choice == 6:
						clear()
						print(f'{header}\nInput the global wrong message\'s new slot number.\nThe slot number must be between 1 and ' + str(len(datafile['wrongmsg'])) + '\nand must not be ' + str(n + 1) + '.\nIt also must not be blank and must not contain non-numeric characters.\nIf above conditions are not met, the move operation will be cancelled.\n')
						try:
							slot = int(input('-----\n\nNew slot number:'))
							if slot >= 1 and slot <= len(datafile['wrongmsg']) and slot != n + 1:
								datafile['wrongmsg'].insert(slot - 1, datafile['wrongmsg'].pop(n))
								if slot != n + 1: modified = True
								n = slot - 1
						except ValueError:
							pass
					elif choice == 7:
						while True:
							clear()
							print(f'{header}\nAre you sure you want to remove this global wrong message?\n(Y: Yes / N: No)')
							key = msvcrt.getwch().lower()
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
			set_title()
			clear()
			print(header)
			if datafile['lives'] < 1: print('[1] Lives                     OFF')
			else: print('[1] Lives                     ' + str(datafile['lives']))
			if datafile['randomize']: print('[2] Shuffle question order    ON')
			else: print('[2] Shuffle question order    OFF')
			if datafile['showcount']: print('[3] Show question count       ON')
			else: print('[3] Show question count       OFF')
			if datafile['wrongmsg']:
				print('[4] Global wrong messages     '  + str(len(datafile['wrongmsg'])) + ' message(s)')
			else: print('[4] Global wrong messages     OFF')
			if datafile['lives'] >= 1:
				if datafile['fail']:
					fail_lines = datafile['fail'].split('\n')
					print('[5] Out of lives message      '  + fail_lines[0])
					if len(fail_lines) >= 1:
						for i in range(1, len(fail_lines)): print('                              '  + fail_lines[i])
				else: print('[5] Out of lives message      OFF')
			else: print('[5] Out of lives message      Requires life setting')
			if datafile['finish']:
				win_lines = datafile['finish'].split('\n')
				print('[6] Win message               '  + win_lines[0])
				if len(win_lines) >= 1:
					for i in range(1, len(win_lines)): print('                              '  + win_lines[i])
			else: print('[6] Win message               None')
			print('[7] Return')

			print('\nPress the number keys on your keyboard to change or toggle a setting.')
			choice = int(msvcrt.getwch())
			if choice == 7: exited_settings = True
			elif choice == 1:
				clear()
				print(f'{header}\nEnter the amount of lives you want to have.\nThe number of lives must be between 1 and 2147483647 and must not be a decimal number.\nIf 0 or lower, the lives setting will be disabled.\nIf blank or contains non-numeric characters,\nprevious life count will be used.\n')
				og = datafile['lives']
				try:
					life = int(input('-----\n\nLives: '))
					if life < 1: datafile['lives'] = 0
					else: datafile['lives'] = life
					if datafile['lives'] != og: modified = True
				except ValueError:
					pass
			elif choice == 2: datafile['randomize'] = not datafile['randomize']; modified = True
			elif choice == 3: datafile['showcount'] = not datafile['showcount']; modified = True
			elif choice == 4: wrongmsgs()
			elif choice == 5:
				if datafile['fail']:
					text = input_string('out of lives message', 'message', datafile['fail'], allow_blank = True)
					datafile['fail'] = text
				else:
					text = input_string('out of lives message', 'message', new = True)
					if text: datafile['fail'] = text
			elif choice == 6:
				if datafile['finish']:
					text = input_string('win message', 'message', datafile['finish'], allow_blank = True)
					if text: datafile['finish'] = text
				else:
					text = input_string('win message', 'message', new = True)
					if text: datafile['finish'] = text

		except ValueError:
			pass
	if datafile['lives'] < 1: del datafile['lives']
	if not datafile['randomize']: del datafile['randomize']
	if datafile['showcount']: del datafile['showcount']
	if len(datafile['wrongmsg']) < 1: del datafile['wrongmsg']
	if len(datafile['fail']) < 1: del datafile['fail']
	if len(datafile['finish']) < 1: del datafile['finish']

def save_menu():
	def save_confirm():
		global savepath
		while True:
			clear()
			print(f'{header}\nSave changes first? (Y: Yes / N: No / C: Cancel)')
			key = msvcrt.getwch().lower()
			if key == 'y': return True
			elif key == 'n': return False
			elif key == 'c': return None
	def save():
		global savepath, savepath_tmp, message, modified, allow_save, is_url
		if args.no_tk:
			path = ''
			tempmsg = 'Is this correct?'
			while True:
				clear()
				print('Type your destination file path.\n')
				if path: keyboard.write(path)
				else: keyboard.write(os.getcwd() + os.sep + datafile['title'] + '.json')
				path = input()
				while True:
					if not path: break
					clear()
					print(tempmsg + '\n\n' + path + '\n\n[ENTER] Confirm | [1] Edit | [2] Cancel')
					tempmsg = ''
					print(tempmsg)
					choice = msvcrt.getwch()
					if (os.name == 'nt' and choice == '\r') or choice == '\n':
						savepath = path
						if os.name == 'nt': savepath.replace('/', '\\')
						if not os.path.exists(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
						try:
							with open(savepath, 'w+') as f: f.write(json.dumps(datafile, indent = 4))
							message = 'JSON file saved as: ' + savepath
							modified = False
							allow_save = True
							is_url = False
							return True
						except IOError as e: tempmsg = 'ERROR: ' + e.strerror
					elif choice == '1': break
					elif choice == '2': return
		else:
			savepath_tmp = ''
			clear()
			savepath_tmp = asksaveasfile(title = 'Where we savin\', boys?', initialdir = os.getcwd(), initialfile = datafile['title'] + '.json', filetypes = [('JSON Files', '*.json'), ('All Files', '*.*')], defaultextension = '.json')
			if savepath_tmp:
				savepath = savepath_tmp
				if os.name == 'nt': savepath.replace('/', '\\')
				try:
					with open(savepath, 'w+') as f: f.write(json.dumps(datafile, indent = 4))
					message = 'JSON file saved as: ' + savepath
					modified = False
					allow_save = True
					is_url = False
					return True
				except IOError as e:
					message = 'Can\'t save file: ' + e.strerror
					return False
	def openf():
		global savepath, savepath_tmp, message, datafile
		if args.no_tk:
			path = ''
			tempmsg = 'Is this correct?'
			while True:
				clear()
				print('Type the file path to your quiz JSON file.\n')
				if path: keyboard.write(path)
				else: keyboard.write(os.getcwd() + os.sep)
				path = input()
				while True:
					if not path: break
					clear()
					print(tempmsg + '\n\n' + path + '\n\n[ENTER] Confirm | [1] Edit | [2] Cancel')
					tempmsg = ''
					choice = msvcrt.getwch()
					if (os.name == 'nt' and choice == '\r') or choice == '\n':
						old_path = savepath
						savepath = path
						if os.name == 'nt': savepath.replace('/', '\\')
						try:
							success = False
							for i in range(1):
								try: datafile = json.load(open(savepath, encoding = 'utf-8'))
								except (json.decoder.JSONDecodeError, UnicodeDecodeError): tempmsg = 'Invalid JSON data!'; savepath = old_path
								if not check_optional_element('title'): tempmsg = 'String variable "title" not found or empty!'; savepath = old_path
								if not check_optional_element('questions', list): tempmsg = 'String variable "questions" not found or empty!'; savepath = old_path
								for i in range(len(datafile['questions'])):
									if not check_question_optional_element('question', i): tempmsg = 'String variable "question" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									if not check_question_optional_element('a', i): tempmsg = 'String variable "a" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									if not check_question_optional_element('b', i): tempmsg = 'String variable "b" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									if not check_question_optional_element('c', i): tempmsg = 'String variable "c" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									if not check_question_optional_element('d', i): tempmsg = 'String variable "d" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									if not check_question_optional_element('correct', i): tempmsg = 'String variable "correct" not found or empty in question ' + str(i+1) + '!'; savepath = old_path
									success = True
								if not success: break
								create_backup()
								message = 'Opened JSON file: ' + savepath
								modified = False
								allow_save = True
								is_url = False
								return
						except IOError as e: tempmsg = 'ERROR: ' + e.strerror
					elif choice == '1': break
					elif choice == '2': return
		else:
			savepath_tmp = ''
			clear()
			savepath_tmp = askopenfilename(title = 'JSON file please!', initialdir = os.getcwd(), filetypes = [('JSON Files', '*.json'), ('All Files', '*.*')], defaultextension = '.json')
			if savepath_tmp:
				old_path = savepath
				savepath = savepath_tmp
				if os.name == 'nt': savepath.replace('/', '\\')
				try:
					success = False
					for i in range(1):
						try: datafile = json.load(open(savepath, encoding = 'utf-8'))
						except (json.decoder.JSONDecodeError, UnicodeDecodeError): message = 'Invalid JSON data!'; savepath = old_path; break
						if not check_optional_element('title'): message = 'String variable "title" not found or empty!'; savepath = old_path; break
						if not check_optional_element('questions', list): message = 'String variable "questions" not found or empty!'; savepath = old_path; break
						for i in range(len(datafile['questions'])):
							if not check_question_optional_element('question', i): message = 'String variable "question" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							if not check_question_optional_element('a', i): message = 'String variable "a" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							if not check_question_optional_element('b', i): message = 'String variable "b" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							if not check_question_optional_element('c', i): message = 'String variable "c" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							if not check_question_optional_element('d', i): message = 'String variable "d" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							if not check_question_optional_element('correct', i): message = 'String variable "correct" not found or empty in question ' + str(i+1) + '!'; savepath = old_path; break
							success = True
						if not success: break
						create_backup()
						message = 'Opened JSON file: ' + savepath
						modified = False
						allow_save = True
						is_url = False
					if not success:
						datafile = datafile_bak.copy()
						create_backup()
				except IOError as e: message = 'Can\'t open file: ' + e.strerror
	global modified, modified_sym, savepath, savepath_tmp, allow_save, datafile, is_url, message
	exited_save = False
	while not exited_save:
		try:
			if modified: modified_sym = '*'
			else: modified_sym = ''
			set_title()
			clear()
			print(header)
			print(message + '\n')
			print('[1] New')
			print('[2] Open...')
			if allow_save: print('[3] Save')
			else: print()
			print('[4] Save as...')
			if modified: print('[5] Reload')
			else: print()
			print('[6] Return')
			message = ''
			print('\nPress the number keys on your keyboard to choose.')
			choice = int(msvcrt.getwch())
			if choice == 6: exited_save = True
			elif choice == 1:
				if modified:
					confirm = save_confirm()
					if confirm != None:
						if (confirm and save()) or not confirm:
							savepath = ''
							datafile = {'title': 'My Quiz', 'questions': [{'question': 'Question', 'a': 'Answer A', 'b': 'Answer B', 'c': 'Answer C', 'd': 'Answer D', 'correct': 'a'}]}
				else:
					savepath = ''
					datafile = {'title': 'My Quiz', 'questions': [{'question': 'Question', 'a': 'Answer A', 'b': 'Answer B', 'c': 'Answer C', 'd': 'Answer D', 'correct': 'a'}]}
			elif choice == 2:
				if modified:
					confirm = save_confirm()
					if confirm != None:
						if (confirm and save()) or not confirm: openf()
				else: openf()
			elif choice == 3:
				if allow_save:
					try:
						with open(savepath, 'w+') as f: f.write(json.dumps(datafile, indent = 4))
						message = 'Saved!'
						modified = False
					except IOError as e: message = 'Can\'t save file: ' + e.strerror
			elif choice == 4: save()
			elif choice == 5:
				if modified:
					while True:
						clear()
						print(f'{header}\nAre you sure you want to reload the current quiz\nand lose your changes made in the editor?\n(Y: Yes / N: No)')
						key = msvcrt.getwch().lower()
						if key == 'y':
							datafile = datafile_bak.copy()
							create_backup()
							modified = False
							message = 'Quiz reloaded.'
							break
						elif key == 'n':
							break
		except ValueError:
			pass

def about():
	set_title('About QuizProg Editor')
	clear()
	print(f'''QUIZPROG EDITOR - VERSION {version}
QUIZPROG VERSION {quizprog_version}''')
	if os.name != 'nt': print('UNIX EDITION')

	print('\n(c) 2022 GamingWithEvets Inc. All rights reserved.\nPress any key to return.')
	msvcrt.getwch()

def set_title(title = None):
	global header
	if title == None:
		if savepath:
			title = 'QuizProg Editor - ' + datafile['title'] + ' - ' + savepath + modified_sym
			header = 'QUIZPROG EDITOR - ' + savepath + modified_sym + '\n'
		else:
			title = 'QuizProg Editor - ' + datafile['title'] + ' - Unsaved quiz' + modified_sym
			header = 'QUIZPROG EDITOR - Unsaved quiz' + modified_sym + '\n'
	if os.name == 'nt': ctypes.windll.kernel32.SetConsoleTitleW(title)
	else: sys.stdout.write('\x1b]2;' + title + '\x07')

quitted = False
error = False
modified = False
modified_sym = ''
message = 'Any save-related messages will appear here.'
if args.path == None: savepath = ''
elif is_url: savepath = args.path
else: savepath = os.path.realpath(args.path)
savepath_tmp = ''
allow_save = args.path != None and not is_url
header = ''

while not quitted:
	try:
		if modified: modified_sym = '*'
		else: modified_sym = ''
		set_title()
		clear()
		print(header)
		print(datafile['title'])
		if check_optional_element('description'): print(datafile['description'])
		else: print('(no description provided)')
		print('\n[1] Rename your quiz')
		print('[2] Add, change or delete quiz description')
		print('[3] Change quiz questions')
		print('[4] Change quiz settings')
		print('\n[5] Save menu')
		print('[6] About QuizProg Editor')
		print('[7] Exit')
		print('\nPress the number keys on your keyboard to choose.')
		choice = int(msvcrt.getwch())
		if choice == 7:
			if modified:
				while True:
					clear()
					print(f'{header}\nExit without saving? (Y: Yes / N: No)')
					key = msvcrt.getwch().lower()
					if key == 'y': quitted = True; break
					elif key == 'n': break
			else: quitted = True
		elif choice == 1:
			text = input_string('quiz name', 'name', datafile['title'], newline = False)
			if text: datafile['title'] = text
		elif choice == 2:
			if check_optional_element('description'):
				text = input_string('quiz description', 'description', datafile['description'], allow_blank = True)
				datafile['description'] = text
			else:
				text = input_string('quiz description', 'description', new = True)
				if text: datafile['description'] = text
		elif choice == 3: change_questions()
		elif choice == 4: change_settings()
		elif choice == 5: save_menu()
		elif choice == 6: about()
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
sys.exit()