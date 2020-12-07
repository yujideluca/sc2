#!/usr/bin/python
##################################################
#
# Filename: TheCoreRemapper.py
# Author: Jonny Weiss, Mark Rösler
# Description: Script to take the LM layouts of TheCore and generate the other 44 layouts.
# Change Log:
#   9/25/12 - Created
#   9/26/12 - Finished initial functionality
#
##################################################
from enum import Enum
import collections  # @UnusedImport
import configparser
import os  # @UnusedImport

from ConflictChecks import *  # @UnresolvedImport @UnusedWildImport
from SameChecks import *  # @UnresolvedImport @UnusedWildImport

class ConfigParser(configparser.ConfigParser):
	"""Case-sensitive ConfigParser."""

	def optionxform(self, opt):
		return opt

	def write(self, file):
		return super().write(file, space_around_delimiters=False)

class Races(Enum):
	Protoss = "P"
	Terran = "T"
	Random = "R"
	Zerg = "Z"

class Sides(Enum):
	Right = "R"
	Left = "L"

class Sizes (Enum):
	Small = "S"
	Medium = "M"
	Large = "L"

class LogLevel(Enum):
	Info = "INFO"
	Warn = "WARN"
	Error = "ERROR"

####################################################################################
## Support for other seeds than the pure TheCore, value = filename
####################################################################################
class OtherSeeds(Enum):
	Lite = "TheCore Lite"
	LiteRehab = "TheCore LiteRehab"
	LitePlus = "TheCore LitePlus"

####################################################################################
## Debug infrastructure
####################################################################################

debug_parser = ConfigParser(allow_no_value=True)
debug = False
try:
	debug_parser.read('Debug.ini')
except:
	print("no Debug.ini file")

debug = debug_parser.getboolean("Settings","debug",fallback=False)
if not(debug):
	debug_parser = ConfigParser()


####################################################################################


class Logger:
	def __init__(self, title, filepath=None, log_file=[LogLevel.Warn, LogLevel.Error], log_consol=[LogLevel.Info, LogLevel.Error]):
		self.title = title
		self.filepath = filepath
		self.log_file = log_file
		self.log_consol = log_consol
		self.messages = {}
		self.messages[LogLevel.Info] = []
		self.messages[LogLevel.Warn] = []
		self.messages[LogLevel.Error] = []
		print(self.get_start_str())

	
	def get_start_str(self):
		output = "============================\n"
		output = output + "Start " + self.title
		if not self.filepath is None:
			output = output + " (log file: " + self.filepath + ")"
		output = output + "\n"
		output = output + "----------------------------"
		return output
	
	def log(self, log_level, msg):
		msg_str = self.get_message_str(log_level, msg)
		self.messages[log_level].append(msg_str)
		if log_level in self.log_consol:
			print(msg_str)
		
	def finish(self):
		output = "----------------------------\n"
		output = output + "Finished (" + self.title + ") - "
		for log_level_file in self.log_file:
			output = output + log_level_file.value + "s: " + str(len(self.messages[log_level_file])) + " "
		output = output + "\n"
		output = output + "============================"
		print(output)
		if not self.filepath is None:
			with open(self.filepath, 'w') as file:
				file.write(self.get_start_str() + "\n")
				for log_level_file in self.log_file:
					for line in self.messages[log_level_file]:
						file.write(line + "\n")
				file.write(output)
		
	def get_message_str(self, log_level, msg):
		msg_str = "[" + log_level.value + "]: " + msg
		if msg.count('\n') > 0:
			msg_str = msg_str + "\n"
		return msg_str

## class Hotkey modified : object structure now allows OtherSeeds
class Hotkey:

	def __init__(self, seeds, name, section, default=None, copyOf=None):
		self.name = name
		self.section = section
		self.key = {}
		self.default = default
		self.copyOf = copyOf
		# init to None for all seed
		for seed in seeds:
			self.key[seed] = None

	def set_value(self, seed, value):
		self.key[seed] = value

	def get_raw_value(self, seed):
		return self.key[seed]

	def get_value(self, seed):
		value = self.get_raw_value(seed)
		if value is None:
			value = self.default
		return value

	def get_values_id(self):
		values = ""
		for seed in self.key:
			value = self.get_value(seed)
			first = True
			alternates = value.split(",")
			alternates.sort()
			for alternate in alternates:
				if first:
					value = alternate
					first = False
				else:
					value = value + "," + alternate
			values = values + seed.value + ":" + value + "\n"
		return values

def init_seed_hotkeyfile_parser():
	hotkeyfile_parsers = {}
	allSeeds = []
	for race in Races:
		hotkeyfile_parser = ConfigParser()
		hotkeyfile_parser.read(create_filepath( prefix + thecore_tag(race, Sides.Left, Sizes.Medium) ) )
		if len(hotkeyfile_parser.sections()) > 0:
			hotkeyfile_parsers[race] = hotkeyfile_parser
			allSeeds.append(race)
	for seed in OtherSeeds:
		hotkeyfile_parser = ConfigParser()
		hotkeyfile_parser.read(create_filepath( seed.value ) )
		if len(hotkeyfile_parser.sections()) > 0:
			hotkeyfile_parsers[seed] = hotkeyfile_parser
			allSeeds.append(seed)
	return hotkeyfile_parsers, allSeeds

def thecore_tag(race, side, size):
	return(" " + race.value + side.value + size.value + " ")

def create_filepath(string, directory=None):
	filename = string + suffix
	filepath = filename
	if directory:
		filepath = directory + "/" + filename
	return filepath

def new_keys_from_seed_hotkeys(default_parser,hotkeyfile_parsers):
	logger = Logger("Search for new Keys in seed layouts", log_consol=[LogLevel.Info], log_file=[])
	for seed in hotkeyfile_parsers:
		for section in hotkeyfile_parsers[seed].sections():
			for item in hotkeyfile_parsers[seed].items(section):
				key = item[0]
				if not default_parser.has_option(section, key):
					default_parser.set(section, key, "")
					logger.log(LogLevel.Info, "New key found " + key + " added to " + default_filepath + " please add a default value")
	with open(default_filepath, 'w') as myfile:
		default_parser.write(myfile)
	order(default_filepath)
	default_parser.read(default_filepath)
	logger.finish()
	return default_parser

def order(filepath):
	read_parser = ConfigParser()
	read_parser.read(filepath)

	dicti = {}
	for section in read_parser.sections():
		items = read_parser.items(section)
		items.sort()
		dicti[section] = items

	open(filepath, 'w').close()  # clear file

	write_parser = ConfigParser()  # on other parser just for the safty
	write_parser.read(filepath)
	write_parser.add_section("Settings")
	write_parser.add_section("Hotkeys")
	write_parser.add_section("Commands")

	for section in dicti.keys():
		if not write_parser.has_section(section):
			write_parser.add_section(section)
		items = dicti.get(section)
		for item in items:
			write_parser.set(section, item[0], item[1])

	with open(filepath, 'w') as myfile:
		write_parser.write(myfile)

def check_defaults(default_parser):
	logger = Logger("Check defaults", "Defaults.log", log_consol=[LogLevel.Error], log_file=[LogLevel.Warn, LogLevel.Error])
	for section in default_parser.sections():
		for item in default_parser.items(section):
			key = item[0]
			default = item[1]
			multidefault = ddefault_parser.has_option(section, key)
			if not default or multidefault:
				seedhas = True
				for seed in hotkeyfile_parsers:
					if not hotkeyfile_parsers[seed].has_option(section, key):
						seedhas = False
				inherit = inherit_parser.has_option(section, key)

				if multidefault:
					if not seedhas and not inherit:
						logger.log(LogLevel.Error, "key has multiple different defaults - please set in all seed layouts a value for this key (or at leased unbound it) " + key)
				if not default:
					if seedhas or inherit:
						logger.log(LogLevel.Warn, "no default " + key)
					else:
						logger.log(LogLevel.Error, "no default " + key)
	logger.finish()

def create_model(seeds):
	model = {}
	for section in default_parser.sections():
		section_dict = {}
		for key in default_parser.options(section):
			hotkey = Hotkey(seeds, key, section, default=default_parser.get(section,key))
			for seed in seeds:
				if hotkeyfile_parsers[seed].has_option(section, key):
					value = hotkeyfile_parsers[seed].get(section, key)
					hotkey.set_value(seed, value)
			if inherit_parser.has_option(section, key):
				copyof = inherit_parser.get(section, key)
				hotkey.copyOf = copyof
			section_dict[key] = hotkey
		model[section] = section_dict
	return model

def generate(seeds,seed_model):
	logger = Logger("Generation", log_consol=[LogLevel.Info], log_file=[])
	seed_models = init_models()
	for seed in seeds:
		if seed in Races:
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: L size: M keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Left][Sizes.Medium] = extract_race(seed_model, seed)
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: R size: M keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Right][Sizes.Medium] = convert_side(seed_models[seed][Sides.Left][Sizes.Medium], Sides.Right)
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: L size: S keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Left][Sizes.Small] = shift_left(seed_models[seed][Sides.Left][Sizes.Medium], Sides.Left)
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: R size: S keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Right][Sizes.Small] = shift_right(seed_models[seed][Sides.Right][Sizes.Medium], Sides.Right)
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: L size: L keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Left][Sizes.Large] = shift_right(seed_models[seed][Sides.Left][Sizes.Medium], Sides.Left)
			logger.log(LogLevel.Info, "generate model for race: " + seed.value + " side: R size: L keyboardlayout: " + seed_layout)
			seed_models[seed][Sides.Right][Sizes.Large] = shift_left(seed_models[seed][Sides.Right][Sizes.Medium], Sides.Right)
		else:
			seed_models[seed] = extract_race(seed_model, seed)
	translate_and_create_files(seed_models, logger)
	logger.finish()

def init_models():
	models = {}
	for race in Races:
		models[race] = {}
		for side in Sides:
			models[race][side] = {}
	return models

def extract_race(seed_model, race):
	model_dict = {}
	for section in seed_model:
		model_dict[section] = {}
		for key, hotkey in seed_model[section].items():
			value = resolve_inherit(seed_model, section, hotkey, race)
			model_dict[section][key] = value
	return model_dict

def resolve_inherit(model, section, hotkey, race):
	hotkey = resolve_copyof(model, section, hotkey)
	value = hotkey.get_value(race)
	return value

def resolve_copyof(model, section, hotkey):
	while True:
		if hotkey.copyOf:
			hotkey = model[section][hotkey.copyOf]
		else:
			return hotkey

def convert_side(seed_model, side):
	return modify_model(seed_model, settings_parser, 'GlobalMaps', side)

def modify_model(seed_model, parser, parser_section, side):
	model_dict = {}
	for section in seed_model:
		model_dict[section] = {}
		for key, value in seed_model[section].items():
			if section == "Settings":
				newvalue = value
			else:
				newvalue = modify_value(value, parser, parser_section, side)
			model_dict[section][key] = newvalue
	return model_dict

def modify_value(org_value, parser, section, side):
	altgr = "0"
	if parser == layout_parser and side == Sides.Right:
		altgr = layout_parser.get(section, "AltGr")

	newalternates = []
	for alternate in org_value.split(","):
		keys = alternate.split("+")
		newkeys = []
		# filter "Shift" only to make sure it is the same output as the old script
		if altgr == "1" and keys.count("Alt") == 1 and keys.count("Control") == 0 and keys.count("Shift") == 0:
			newkeys.append("Control")
		for key in keys:
			if parser.has_option(section, key):
				newkey = parser.get(section, key)
			else:
				newkey = key
			newkeys.append(newkey)
		newalternate = ""
		first = True
		for newkey in newkeys:
			if not first:
				newalternate = newalternate + "+"
			else:
				first = False
			if not newkey:
				newalternate = ""
			else:
				newalternate = newalternate + newkey
		newalternates.append(newalternate)
	first = True
	newvalues = ""
	for newalternate in newalternates:
		if not newalternate:
			continue
		if not first:
			newvalues = newvalues + ","
		else:
			first = False
		newvalues = newvalues + newalternate
	return newvalues

def shift_left(seed_model, side):
	shift_section = side.value + 'ShiftLeftMaps'
	return shift(seed_model, shift_section, side)

def shift_right(seed_model, side):
	shift_section = side.value + 'ShiftRightMaps'
	return shift(seed_model, shift_section, side)

def shift(seed_model, shift_section, side):
	return modify_model(seed_model, settings_parser, shift_section, side)

def translate_and_create_files(models, logger):
	layouts = layout_parser.sections()
	for layout in layouts:
		for seed in allSeeds:
			if seed in Races:
				for side in Sides:
					for size in Sizes:
							if layout != seed_layout:
								logger.log(LogLevel.Info, "translate seed: " + seed.value + " side: " + side.value + " size: " + size.value + " keyboardlayout: " + layout)
								model = translate(models[seed][side][size], layout, side)
							else:
								model = models[seed][side][size]
							filename = prefix + thecore_tag(seed, side, size)
							create_file(model, filename, layout, logger)
			else:
				if layout != seed_layout:
					logger.log(LogLevel.Info, "translate seed: " + seed.value + " keyboardlayout: " + layout)
					model = translate(models[seed], layout, Sides.Left)
				else:
					model = models[seed]
				create_file(model, seed.value, layout, logger)

def translate(seed_model, layout, side):
	return modify_model(seed_model, layout_parser, layout, side)

def create_file(model, filename, layout, logger):
	hotkeyfile_parser = ConfigParser()
	for section in model:
		if not hotkeyfile_parser.has_section(section):
				hotkeyfile_parser.add_section(section)
		for key, value in model[section].items():
			hotkeyfile_parser.set(section, key, value)
	if not os.path.isdir(layout):
		os.makedirs(layout)
	filepath = create_filepath(filename, layout)
	hotkeyfile = open(filepath, 'w')
	hotkeyfile_parser.write(hotkeyfile)
	hotkeyfile.close()
	order(filepath)
	logger.log(LogLevel.Info, filepath + " created")
	return filepath

def analyse(model):
	## default checks
	same_check(model)
	conflict_check(model)
	wrong_inherit(model)
	## context dependent checks
	CheckConsistency(model)
	hotkey_command_check(model)
	unbound_command_check(model)
	## quality checks accross seeds
	if debug_parser.getboolean("Settings","quality",fallback=True):
		stable_regression_check(model)
		suggest_inherit(model)
		missing_conflict_check(model)

def same_check(model):
	logger = Logger("same check", "SameCheck.log", log_consol=[], log_file=[LogLevel.Error])
	for seed in allSeeds:
		for same_set in SAME_CHECKS:  # @UndefinedVariable
			same_set.sort()
			first_key = same_set[0]
			for section in collections.OrderedDict(sorted(model.items())):
				if not first_key in model[section]:
					continue
				mismatched = False
				value = model[section][first_key].get_value(seed)
				for key in same_set:
					if not model[section][key].get_value(seed) == value:
						mismatched = True
				if mismatched:
					log_msg = "Mismatched values in seed: " + seed.value
					for key in same_set:
						log_msg = log_msg + "\n\t" + key + " = " + model[section][key].get_value(seed)
					logger.log(LogLevel.Error, log_msg)
	logger.finish()

def conflict_check(model):
	logger = Logger("conflict check", "ConflictCheck.log", log_consol=[], log_file=[LogLevel.Error])
	for seed in allSeeds:
		for commandcard_key, conflict_set in collections.OrderedDict(sorted(CONFLICT_CHECKS.items())).items():  # @UndefinedVariable
			if not(commandcard_key in constraints['ToCheck']['Conflicts']):
				continue
			conflict_set.sort()
			count_hotkeys = {}
			for section in model:
				for key, hotkey in model[section].items():
					if key in conflict_set:
						values = hotkey.get_value(seed).split(",")
						for value in values:
							if not value:
								continue
							if not value in count_hotkeys:
								count_hotkeys[value] = 1
							else:
								count_hotkeys[value] = count_hotkeys[value] + 1
			
			
			for value, count in collections.OrderedDict(sorted(count_hotkeys.items())).items():
				if count > 1:
					log_msg = "Conflict of hotkeys in seed: " + seed.value + " commandcard: " + commandcard_key
					issue_keys = []
					for key in conflict_set:
						for section in collections.OrderedDict(sorted(model.items())):
							if not key in model[section]:
								continue
							raw_values = model[section][key].get_value(seed)
							values = raw_values.split(",")
							values.sort()
							issue = False
							for issue_value in values:
								if issue_value == value:
									issue = True
									issue_keys.append(key)
							if issue:
								log_msg + log_msg + "\n\t" + key + " = " + raw_values
					if debug_parser.getboolean("Settings","verbose",fallback=False):
						log_msg += "\nCommand in conflict :"
						hint=""
						for issue_key in issue_keys:
							log_msg += "\n- " + issue_key
							tmp_hint = remapHint(issue_key, seed, log=True)
							if hint=="" or tmp_hint.count("\n")<hint.count("\n"):
								hint=tmp_hint
						log_msg += hint
					logger.log(LogLevel.Error, log_msg)
	logger.finish()
				
def suggest_inherit(model):
	logger = Logger("suggest inherit", "SuggestInheritance.log", log_consol=[], log_file=[LogLevel.Info])
	outputdict = {}
	for section in model:
		outputdict[section] = {}
		for hotkey1 in model[section].values():
			values_id = hotkey1.get_values_id()
			for hotkey2 in model[section].values():
				if hotkey1.name == hotkey2.name:
					continue
				equal = True
				for seed in allSeeds:
					value = hotkey1.get_value(seed)
					value2 = hotkey2.get_value(seed)
					value_set = set(str(value).split(","))
					value2_set = set(str(value2).split(","))
					if value_set != value2_set:
						equal = False
						break
				if equal:
					if not values_id in outputdict[section]:
						outputdict[section][values_id] = {}
					if not hotkey1.name in outputdict[section][values_id]:
						outputdict[section][values_id][hotkey1.name] = hotkey1
					if not hotkey2.name in outputdict[section][values_id]:
						outputdict[section][values_id][hotkey2.name] = hotkey2

	for section in collections.OrderedDict(sorted(outputdict.items())):
		for values_id in collections.OrderedDict(sorted(outputdict[section].items())):
			hotkeys = outputdict[section][values_id]
			first = True
			log_msg = ""
			for hotkey in collections.OrderedDict(sorted(hotkeys.items())).values():
				if first:
					for seed in allSeeds:
						value = hotkey.get_value(seed)
						log_msg = log_msg + seed.value + ": " + str(value) + "   "
					first = False
				log_msg = log_msg + "\n\t" + hotkey.name + " default: " + hotkey.default
				if hotkey.copyOf:
					hotkeycopyof = model[section][hotkey.copyOf]
					log_msg = log_msg + " copyof: " + hotkeycopyof.name + " default: " + hotkeycopyof.default
			logger.log(LogLevel.Info, log_msg)
	logger.finish()

def wrong_inherit(model):
	logger = Logger("wrong inherit", "WrongInheritance.log", log_consol=[], log_file=[LogLevel.Error,LogLevel.Warn])
	for section in collections.OrderedDict(sorted(model.items())):
		for hotkey in collections.OrderedDict(sorted(model[section].items())).values():
			if not hotkey.copyOf:
				continue
			hotkeycopyof = resolve_copyof(model, section, hotkey)
			equal = True
			for seed in allSeeds:
				value = hotkey.get_value(seed)
				copyofvalue = hotkeycopyof.get_value(seed)
				value_set = set(str(value).split(","))
				copyofvalue_set = set(str(copyofvalue).split(","))
				if value_set != copyofvalue_set:
					equal = False
			if not equal:
				log_msg = hotkey.name + " != " + hotkeycopyof.name + "\n"
				log_lvl = LogLevel.Warn
				for seed in allSeeds:
					value = hotkey.get_raw_value(seed)
					copyofvalue = hotkeycopyof.get_value(seed)
					if not value:
						value = " "
					if not copyofvalue:
						copyofvalue = " "
					if value.split(",")[0] != copyofvalue.split(",")[0]:
						log_lvl = LogLevel.Error
					log_msg = log_msg + "\t" + seed.value + ": " + str(value) + "\t" + str(copyofvalue) + "\n"
				default = hotkey.default
				if not default:
					default = " "
				copyofdefault = hotkeycopyof.default
				if not copyofdefault:
					copyofdefault = " "
				log_msg = log_msg + "\tD: " + str(default) + "\t" + str(copyofdefault) + " (default)"
				logger.log(log_lvl, log_msg)
	logger.finish()



def hotkey_command_check(model):
	logger = Logger("command conflicts with hotkeys", "HotkeyCommandCheck.log", log_consol=[], log_file=[LogLevel.Error])
	for seed in allSeeds:
		hotkey_list = getHotkeyList(seed,'Hotkeys')
		for command in sorted(hotkeyfile_parsers[seed].options('Commands')):
			for key in model['Commands'][command].get_value(seed).split(','):
				if key in hotkey_list:
					log_msg = key + " used for command "+ command +", in seed " + seed.value
					logger.log(LogLevel.Error, log_msg)
	logger.finish()

def unbound_command_check(model):
	logger = Logger("unbound commands, within identified conflicts", "UnboundCommandCheck.log", log_consol=[], log_file=[LogLevel.Error])
	for seed in allSeeds:
		## Find&Report context unbound command within CONFLICT_CHECKS
		for command in sorted(hotkeyfile_parsers[seed].options('Commands')):
			for key in model['Commands'][command].get_value(seed).split(','):
				if key == '':
					log_msg = ' unbound command ' + command +", in seed " + seed.value
					if debug_parser.getboolean("Settings","verbose",fallback=False):
						 log_msg += remapHint(command, seed, log=True)
					logger.log(LogLevel.Error, log_msg)
	logger.finish()

def missing_conflict_check(model):
	logger = Logger("commands with no attached conflict", "MissingConflict.log", log_consol=[], log_file=[LogLevel.Error, LogLevel.Warn])
	## check for missing conflicts, temperate if part of SAME_CHECKS or inheritance.ini
	for command in default_parser.options('Commands'):
		if not(command in constraints['CommandInfo']['HasConflict']):
			log_msg = command + " not related to a conflict"
			level = LogLevel.Error
			if command in constraints['CommandInfo']['HasSame']:
				log_msg += "\nbut is part of same check"
				level = LogLevel.Warn
			if command in constraints['CommandInfo']['HasInherit']:
				log_msg += "\nbut is inherited"
				level = LogLevel.Warn
			for seed in allSeeds:
				log_msg += "\nin seed " + seed.value + ", keys =" + model['Commands'][command].get_value(seed)
			logger.log(level, log_msg)
	logger.finish()

def stable_regression_check(model,stableDir='stable'):
	logger = Logger("Regression against referenced seeds", "StableRegression.log", log_consol=[LogLevel.Info], log_file=[LogLevel.Error, LogLevel.Warn, LogLevel.Info])
	pairlist = []
	for race in Races:
		if race in allSeeds:
			filename = create_filepath( prefix + thecore_tag(race, Sides.Left, Sizes.Medium), 'stable')
			if os.path.isfile(filename):
				pairlist.append( (seed,filename) )
	for seed in OtherSeeds:
		if seed in allSeeds:
			filename = create_filepath( seed.value, 'stable')
			if os.path.isfile(filename):
				pairlist.append( (seed,filename) )
	for seed, filename in pairlist:
		log_msg = "seed '"+seed.value+"' got regression check against '"+filename+"'"
		logger.log(LogLevel.Info, log_msg)
		ref_parser = ConfigParser()
		ref_parser.read(default_filepath)
		ref_parser.read(filename)
		for section in model.keys():
			## Check Commands
			if section == 'Commands':
				commandToCheck={}
				for context in ['LotV Multiplayer','HotS Multiplayer','libertymulti','swarmmulti','voidmulti']:
					for command in constraints['CommandByContexts'][context]:
						commandToCheck[command]=0
				for command in sorted(commandToCheck):
					if model['Commands'][command].get_value(seed) != ref_parser['Commands'][command]:
						log_msg = "'" +model['Commands'][command].get_value(seed) + "' used in place of '" + ref_parser['Commands'][command] + "' for command '"+ command + "', in seed '" + seed.value + "'"
						logger.log(LogLevel.Warn, log_msg)
			else:
				for param in sorted(model[section].keys()):
					if model[section][param].get_value(seed) != ref_parser[section][param]:
						log_msg =  model[section][param].get_value(seed) + " used in place of " + ref_parser[section][param] + " for parameter "+ param +", in seed " + seed.value
						logger.log(LogLevel.Error, log_msg)
	logger.finish()

def getConstraints():
	## init the constraints dict
	constraints = {}
	constraints['CommandInfo'] = {}
	constraints['ConflictByContexts'] = {}
	constraints['CommandByContexts'] = {}
	constraints['CommandConflicts'] = {}
	constraints['CommandContexts'] = {}
	constraints['ToCheck'] = {}
	## sublevels init
	constraints['CommandInfo']['HasSame'] = []
	constraints['CommandInfo']['HasInherit'] = []
	constraints['CommandInfo']['HasConflict'] = []
	constraints['ToCheck']['Commands'] = []
	constraints['ToCheck']['Conflicts'] = []
	## Add 'HasSame' info
	for same in SAME_CHECKS:
		if not same in constraints['CommandInfo']['HasSame']:
			constraints['CommandInfo']['HasSame'] += same
	## Add 'HasInherit' info
	constraints['CommandInfo']['HasInherit'] = inherit_parser.options('Commands')
	## Create context/command/conflict keys
	for conflict in CONFLICT_CHECKS:
		context = conflict.split("/")[0]
		constraints['CommandByContexts'][context]=[]
		constraints['ConflictByContexts'][context]=[]
		for command in CONFLICT_CHECKS[conflict]:
			constraints['CommandConflicts'][command]=[]
			constraints['CommandContexts'][command]=[]
	## Conflict related constraints
	for conflict in CONFLICT_CHECKS:
		context = conflict.split("/")[0]
		if not(conflict in constraints['ConflictByContexts'][context]):
			constraints['ConflictByContexts'][context].append(conflict)
		for command in CONFLICT_CHECKS[conflict]:
			constraints['CommandConflicts'][command].append(conflict)
			if not(context in constraints['CommandContexts'][command]):
				constraints['CommandContexts'][command].append(context)
			if not(command in constraints['CommandInfo']['HasConflict']):
				constraints['CommandInfo']['HasConflict'].append(command)
			if not(command in constraints['CommandByContexts'][context]):
				constraints['CommandByContexts'][context].append(command)
	## ToCheck generation
	for context in constraints['CommandByContexts']:
		if debug:
			if context in debug_parser.options("IgnoredContexts"):
				print('INFO: Ignored context : ' + context)
				continue
		for command in constraints['CommandByContexts'][context]:
			if not(command in constraints['ToCheck']['Commands']):
				constraints['ToCheck']['Commands'].append(command)
		for conflict in constraints['ConflictByContexts'][context]:
			if not(conflict in constraints['ToCheck']['Conflicts']):
				constraints['ToCheck']['Conflicts'].append(conflict)
	## Sort ToCheck entries + produce info
	for entry in sorted(constraints['ToCheck']):
		constraints['ToCheck'][entry].sort()
		print(entry + ' to check : ' + str(len(constraints['ToCheck'][entry])))
	## Return constraints dict
	return constraints

def getHotkeyList(seed,section,ignoredCommands=['TargetChoose','TargetCancel']):
	hotkey_list = []
	for command in hotkeyfile_parsers[seed].options(section):
		if not command in ignoredCommands:
			for hotkey in  hotkeyfile_parsers[seed].get(section,command).split(','):
				if hotkey != '' and hotkey.count('+') == 0 and not(hotkey in hotkey_list):
					hotkey_list.append(hotkey)
	return hotkey_list

def remapHint(command, seed, log=False):
	if debug_parser.getboolean("Settings","verydetail",fallback=not(log)):
		hint = 'Remap hints for command: ' + command + '\n'
	else:
		hint = ''
	listForbiddenKeys = []
	for conflict in sorted(constraints['ToCheck']['Conflicts']):
		if command in sorted(CONFLICT_CHECKS[conflict]):
			if debug_parser.getboolean("Settings","verydetail",fallback=not(log)):
				hint += "-CONFLICT- " + conflict + '\n'
			for otherCommand in sorted(CONFLICT_CHECKS[conflict]):
				keys = model['Commands'][otherCommand].get_value(seed)
				if debug_parser.getboolean("Settings","verydetail",fallback=not(log)):
					hint += keys + "\t" + otherCommand + '\n'
				for key in keys.split(','):
					if not(key in listForbiddenKeys):
						listForbiddenKeys.append(key)
	hint += 'List of forbidden keys:\n'
	hint += str(listForbiddenKeys)
	if log:
		return("\n"+hint)
	else:
		print(hint)

###########################################
# Section related to Meta .SC2Hotkeys
###########################################

def CheckConsistency(model, write=False):
	logger = Logger("Check key reuse over common CommandRoot", "CommandRootConsistency.log", log_file=[LogLevel.Error])
	for seed in allSeeds:
		metaseed_parser = ConfigParser()
		## Settings&Hotkey section
		for section in ['Settings','Hotkeys']:
			metaseed_parser.add_section(section)
			for option in hotkeyfile_parsers[seed].options(section):
				metaseed_parser.set(section,option,hotkeyfile_parsers[seed].get(section,option))
		## Command section
		metaseed_parser.add_section('Commands')
		tmp_dict2 = {}
		tmp_dict2['keys'] = {}
		tmp_dict2['ok'] = {}
		for command in sorted(model['Commands']):
			command_list = command.split('/')
			if len(command_list) > 1:
				if command_list[1] in ['VoidRift','VoidRiftUnselectable','SuperWarpGate','VoidThrasher','VoidThrasherWalker','Epilogue02VoidRift','SJMercStarport','MercCompound','PrimalTownHallUprooted','PrimalTownHall','MutaliskViper','Bunker','Colossus','ColossusPurifier']:
					metaseed_parser.set('Commands',command,model['Commands'][command].get_value(seed))
					continue
			command_root = command_list[0]
			if not( command_root in tmp_dict2['ok'] ):
				tmp_dict2['ok'][command_root] = True
			if tmp_dict2['ok'][command_root] == True:
				keys = model['Commands'][command].get_value(seed).split(',')
				if not( command_root in tmp_dict2['keys'] ):
					tmp_dict2['keys'][command_root] = keys
					metaseed_parser.set('Commands',command_root,model['Commands'][command].get_value(seed))
				else:
					if keys != tmp_dict2['keys'][command_root]:
						log_msg = "'" +command_root+"' is not consistent in seed '" + seed.value + "'"
						logger.log(LogLevel.Error, log_msg)
						tmp_dict2['ok'][command_root] = False
		if write:
			with open(seed.value+".SC2HotkeysMeta",'w') as myfile:
				metaseed_parser.write(myfile)
	logger.finish()

#def load_meta(seeds=allSeeds):
#	model = {}
#	for section in default_parser.sections():
#		section_dict = {}
#		for key in default_parser.options(section):
#			hotkey = Hotkey(key, section)
#			hotkey.default = default_parser.get(section,key)
#			for seed in seeds:
#				if hotkeyfile_parsers[seed].has_option(section, key):
#					value = hotkeyfile_parsers[seed].get(section, key)
##					## meta enabled case:  (could be built recurusively
##					if debug_parser.getboolean("Settings","enablemeta",fallback=False):
##						if hotkeyfile_parsers[seed].has_option(section, value):
##							value = hotkeyfile_parsers[seed].get(section, value)
#					hotkey.set_value(seed, value)
###					continue
##				## consider command root if in the meta file
##				if debug_parser.getboolean("Settings","enablemeta",fallback=False):
##					command_root = key.split("/")[0]
##					if hotkeyfile_parsers[seed].has_option(section, command_root):
##						value = hotkeyfile_parsers[seed].get(section, command_root)  #
##						hotkey.set_value(seed, value)
#			if inherit_parser.has_option(section, key):
#				copyof = inherit_parser.get(section, key)
#				hotkey.copyOf = copyof
#			section_dict[key] = hotkey
#		model[section] = section_dict
#	return model



####################################################################################
## MAIN
####################################################################################

print("""
  ________         ______
 /_  __/ /_  ___  / ____/___  ________
  / / / __ \/ _ \/ /   / __ \/ ___/ _ \\
 / / / / / /  __/ /___/ /_/ / /  /  __/
/_/ /_/ /_/\___/\____/\____/_/   \___/
   ______                           __
  / ____/___  ____ _   _____  _____/ /____  _____
 / /   / __ \/ __ \ | / / _ \/ ___/ __/ _ \/ ___/
/ /___/ /_/ / / / / |/ /  __/ /  / /_/  __/ /
\____/\____/_/ /_/|___/\___/_/   \__/\___/_/
""")

# Read the settings
settings_parser = ConfigParser()
settings_parser.read('MapDefinitions.ini')
prefix = settings_parser.get("Filenames", "Prefix")
suffix = settings_parser.get("Filenames", "Suffix")
seed_layout = settings_parser.get("Filenames", "Seed_files_folder")

layout_parser = ConfigParser()
layout_parser.read('KeyboardLayouts.ini')

default_filepath = 'Defaults.ini'
default_parser = ConfigParser()
default_parser.read(default_filepath)

ddefault_filepath = 'DifferentDefault.ini'
ddefault_parser = ConfigParser()
ddefault_parser.read(ddefault_filepath)

inherit_filepath = 'Inheritance.ini'
inherit_parser = ConfigParser()
inherit_parser.read(inherit_filepath)

## Consider all existing seeds for defaults handling/checks
hotkeyfile_parsers, allSeeds = init_seed_hotkeyfile_parser()
if debug_parser.getboolean("Settings","update_default",fallback=True):
	default_parser = new_keys_from_seed_hotkeys(default_parser,hotkeyfile_parsers)
check_defaults(default_parser)

## Possibly reduce seed list to be considered
if not(debug_parser.getboolean("Settings","allseeds",fallback=True)):
	allSeeds = []
	for race in debug_parser.options("Races"):
		allSeeds.append(Races[race])
	for seed in debug_parser.options("OtherSeeds"):
		allSeeds.append(OtherSeeds[seed])

## Create model based on wanted seeds
model = create_model(allSeeds)
if debug_parser.getboolean("Settings","generate",fallback=True):
	generate(allSeeds,model)

## Check model against constraints
constraints = getConstraints()
analyse(model)
