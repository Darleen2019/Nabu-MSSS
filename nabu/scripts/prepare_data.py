"""dataprep.py
does the data preperation for a single database"""

import sys
import os
import subprocess
import shutil
from six.moves import configparser
import tensorflow as tf
import data
sys.path.append(os.getcwd())


def main(expdir, recipe, computing, minmemory):
	"""main method"""
		
	if recipe is None:
		raise Exception('no recipe specified. Command usage: run data --recipe=/path/to/recipe')
	if not os.path.isdir(recipe):
		raise Exception('cannot find recipe %s' % recipe)
	if expdir is None:
		raise Exception(
			'no expdir specified. Command usage: run data --expdir=/path/to/recipe --recipe=/path/to/recipe')
	if computing not in ['standard', 'condor']:
		raise Exception('unknown computing mode: %s' % computing)

	# read the data conf file
	parsed_cfg = configparser.ConfigParser()
	parsed_cfg.read(os.path.join(recipe, 'database.conf'))
	cfg_sections = parsed_cfg.sections()
	exp_specific_computing_cfg_file = os.path.join(recipe, 'computing.cfg')
	if os.path.isfile(exp_specific_computing_cfg_file) and computing != 'standard' and not minmemory:
		parsed_exp_specific_computing_cfg = configparser.ConfigParser()
		parsed_exp_specific_computing_cfg.read(exp_specific_computing_cfg_file)
		exp_specific_computing_cfg = dict(parsed_exp_specific_computing_cfg.items('computing'))
		minmemory = exp_specific_computing_cfg['mindatamemory']
	
	# check which parameters are defined globaly for database
	if 'globalvars' in cfg_sections:
		globaldataconf = dict(parsed_cfg.items('globalvars'))

		cfg_sections.remove('globalvars')

	# loop over the sections in the data config
	for name in cfg_sections:

		print('processing %s' % name)

		# read the section
		conf = dict(parsed_cfg.items(name))

		if conf['preprocess'] == 'True':
			# create the expdir for this section
			if not os.path.isdir(os.path.join(expdir, name)):
				os.makedirs(os.path.join(expdir, name))

			# create the database configuration
			dataconf = configparser.ConfigParser()
			dataconf.add_section(name)
			for item in conf:
				if conf[item] == 'globalvars':
					dataconf.set(name, item, globaldataconf[item])
				else:
					dataconf.set(name, item, conf[item])

			with open(os.path.join(expdir, name, 'database.cfg'), 'w') as fid:
				dataconf.write(fid)

			# copy the processor config
			shutil.copyfile(
				conf['processor_config'],
				os.path.join(expdir, name, 'processor.cfg'))
			#
			computing_cfg_file = 'config/computing/%s/%s.cfg' % (computing, 'non_distributed')

			if computing == 'condor':
				if not minmemory:
					# read the computing config file
					parsed_computing_cfg = configparser.ConfigParser()
					parsed_computing_cfg.read(computing_cfg_file)
					computing_cfg = dict(parsed_computing_cfg.items('computing'))
					minmemory = computing_cfg['mindatamemory']

				if not os.path.isdir(os.path.join(expdir, name, 'outputs')):
					os.makedirs(os.path.join(expdir, name, 'outputs'))
				subprocess.call([
					'condor_submit', 'expdir=%s' % os.path.join(expdir, name), 'memory=%s' % minmemory,
					'nabu/computing/condor/dataprep.job'])
			else:
				data.main(os.path.join(expdir, name))

		else:
			print('Did not require storage.')


if __name__ == '__main__':

	tf.app.flags.DEFINE_string('expdir', None, 'the exeriments directory')
	tf.app.flags.DEFINE_string('recipe', None, 'The directory containing the recipe')
	tf.app.flags.DEFINE_string('computing', 'standard', 'the distributed computing system one of condor')
	tf.app.flags.DEFINE_string('minmemory', None, 'The minimum required computing RAM in MB. (only for non-standard computing)')
	tf.app.flags.DEFINE_string('sweep_flag', 'False', 'wheter the script was called from a sweep')

	FLAGS = tf.app.flags.FLAGS

	if FLAGS.minmemory == 'None':
		FLAGS.minmemory = None

	main(FLAGS.expdir, FLAGS.recipe, FLAGS.computing, FLAGS.minmemory)
