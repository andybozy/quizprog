import os
import random
import json
import traceback

version = '0.1.0'

import argparse
parser = argparse.ArgumentParser(description = 'Loads a pre-made quiz from a JSON.', epilog = 'QuizProg v{0}\n(c) 2022 GamingWithEvets Inc. All rights reserved.'.format(version), formatter_class = argparse.RawTextHelpFormatter, allow_abbrev = False)
parser.add_argument('path', metavar = 'json_path', help = 'path to your JSON file')
args = parser.parse_args()
path = args.path
if not os.path.exists(path): parser.error('invalid JSON file path')
try:
	datafile = json.load(open(path, 'r', encoding = 'utf-8'))
except:
	parser.error('invalid JSON file.\n' + traceback.format_exc())

def clear():
	done = False
	while not done:
		try:
			if os.name == 'nt': os.system('cls')
			else: os.system('clear')
			done = True
		except:
			pass

def check_element(element, jsondata = None):
	if jsondata == None:
		if element not in datafile: parser.error('element "' + element + '" is required')
	else:
		if element not in datafile: parser.error('element "' + element + '" in "' + jsondata + '" is required')

def check_question_element(element, qid):
	if element not in datafile['questions'][qid]: parser.error('element "' + element + '" in question ' + str(qid + 1) + ' is required')

def check_optional_element(element, jsondata = None):
	if jsondata == None:
		if element not in datafile: return False
		else: return True
	else:
		if element not in datafile[jsondata]: return False
		else: return True

def check_question_optional_element(element, qid):
	if element not in datafile['questions'][qid]: return False
	else: return True

check_element('title')
check_element('questions')
if len(datafile['questions']) < 1: parser.error('there must be at least one question in "questions"')
for i in range(len(datafile['questions'])):
	check_question_element('question', i)
	check_question_element('a', i)
	check_question_element('b', i)
	check_question_element('c', i)
	check_question_element('d', i)
	check_question_element('correct', i)

def load_quizzes():
	allow_lives = False
	lives = 0
	if check_optional_element('lives'):
		allow_lives = True
		lives = datafile['lives']
	def quit_confirm():
		while True:
			clear()
			print('ARE YOU SURE?\n')
			print('Are you sure you want to quit the quiz?')
			print('You will lose all your progress.\n')
			inputt = input('Quit the quiz? [Y/N] ').lower()
			if inputt == 'y': return True
			elif inputt == 'n': return False
			else: pass

	rangelist = {}
	for i in range(len(datafile['questions'])):
		rangelist[i] = i

	if check_optional_element('randomize') and type(datafile['randomize']) is bool and datafile['randomize']:
		templist = list(rangelist.values())
		random.shuffle(templist)
		rangelist = dict(zip(rangelist, templist))

	for i in rangelist:
		question_data = datafile['questions'][rangelist[i]]
		print_wrong = False
		answered = False
		while not answered:
			clear()
			if allow_lives:
				if lives < 1:
					print('OUT OF LIVES!\n')
					if check_optional_element('fail'): print(datafile['fail'] + '\n')
					else: print('Uh oh! You ran out of lives. But don\'t worry!\nJust be better next time. ;)')
					print('CORRECT ANSWER: [{0}] {1}\n'.format(question_data['correct'].upper(), question_data[question_data['correct']]))
					input('Press Enter to return.')
					return
				else: print('LIVES: {0}/{1}'.format(lives, datafile['lives']))
			if check_optional_element('showcount') and type(datafile['showcount']) is bool and not datafile['showcount']:
				print('QUESTION {0}\n'.format(i + 1))
			else: print('QUESTION {0}/{1}\n'.format(i + 1, len(datafile['questions'])))
			print(question_data['question'] + '\n')
			print('[A] ' + question_data['a'])
			print('[B] ' + question_data['b'])
			print('[C] ' + question_data['c'])
			print('[D] ' + question_data['d'] + '\n')
			print('[E] Quit\n')
			if print_wrong:
				if check_question_optional_element('wrongmsg', i) and choice in question_data['wrongmsg']:
					print(question_data['wrongmsg'][choice] + '\n')
				else:
					if allow_lives: print('Choice ' + choice.upper() + ' is incorrect! You lost a life!\n')
					else: print('Choice ' + choice.upper() + ' is incorrect!\n')

			choice = input('Your choice: ').lower()
			if choice in ['a', 'b', 'c', 'd']:
				if question_data['correct'] == 'all': answered = True
				elif choice == question_data['correct']: answered = True
				else:
					if choice:
						if allow_lives: lives -= 1
						print_wrong = True
			elif choice == 'e':
				if quit_confirm(): return
		clear()
		if allow_lives: print('LIVES: {0}/{1}'.format(lives, datafile['lives']))
		print('CORRECT!\n')
		if check_question_optional_element('explanation', i): print(question_data['explanation'] + '\n')
		input('Press Enter to continue.')
	clear()
	print('IT\'S THE END OF THE QUIZ!\n')
	if check_optional_element('finish'): print(datafile['finish'] + '\n')
	input('Press Enter to return.')

quitted = False
error = False
while not quitted:
	try:
		clear()
		print(datafile['title'].upper())
		print('\nPowered by QuizProg v' + version + '\n')
		if check_optional_element('description'): print(datafile['description'])
		print('\n[1] Start')
		print('[2] Quit\n')

		choice = int(input('Your choice: '))
		if choice == 2: quitted = True
		elif choice == 1: load_quizzes()
		else: pass

	except ValueError:
		pass
	except KeyboardInterrupt:
		clear()
		print('Detected Ctrl+C hotkey.')
		print(traceback.format_exc())
		error = True
		quitted = True
	except:
		clear()
		print('An error has occurred.')
		print(traceback.format_exc())
		error = True
		quitted = True

if not error: clear()
exit()