"""@file task_evaluator.py
contains the TaskEvaluator class"""

from abc import ABCMeta, abstractmethod
import tensorflow as tf
from nabu.processing import input_pipeline
import numpy as np


class TaskEvaluator(object):
	"""the general evaluator class

	an evaluator is used to evaluate the performance of a model"""

	__metaclass__ = ABCMeta

	def __init__(self, conf, dataconf, models,  task):
		"""TaskEvaluator constructor

		Args:
			conf: the evaluator configuration as a ConfigParser
			dataconf: the database configuration
			models: the models to be evaluated
		"""

		self.conf = conf
		self.models = models
		self.task = task
		task_eval_conf = dict(conf.items(task))

		if 'requested_utts' in task_eval_conf:
			self.requested_utts = int(task_eval_conf['requested_utts'])
		else:
			self.requested_utts = int(self.conf.get('evaluator', 'requested_utts'))
		if 'batch_size' in task_eval_conf:
			self.batch_size = int(task_eval_conf['batch_size'])
		else:
			self.batch_size = int(self.conf.get('evaluator', 'batch_size'))

		# get the database configurations for all inputs, outputs, intermediate model nodes and models.
		self.output_names = task_eval_conf['outputs'].split(' ')
		self.input_names = task_eval_conf['inputs'].split(' ')
		self.model_nodes = task_eval_conf['nodes'].split(' ')
		self.target_names = task_eval_conf['targets'].split(' ')
		if self.target_names == ['']:
			self.target_names = []

		if 'linkedsets' in task_eval_conf:
			set_names = task_eval_conf['linkedsets'].split(' ')
			self.linkedsets = dict()
			for set_name in set_names:
				set_input_names = ['%s_%s' % (set_name, in_name) for in_name in self.input_names]
				set_target_names = ['%s_%s' % (set_name, tar_name) for tar_name in self.target_names]
				self.linkedsets[set_name] = {'inputs': set_input_names, 'targets': set_target_names}

			if 'linkedset_weighting' in task_eval_conf:
				linkedset_weighting = np.array(map(float, task_eval_conf['linkedset_weighting'].split(' ')))
				# the first set has the reference weight
				linkedset_weighting /= linkedset_weighting[0]
			else:
				linkedset_weighting = np.array([1.0] * len(self.linkedsets))
			self.linkedset_weighting = {set_name: weight for set_name, weight in zip(set_names, linkedset_weighting)}
		else:
			self.linkedsets = {'set0': {'inputs': self.input_names, 'targets': self.target_names}}
			self.linkedset_weighting = {'set0': 1.0}

		self.input_dataconfs = dict()
		self.target_dataconfs = dict()
		for linkedset in self.linkedsets:
			self.input_dataconfs[linkedset] = []
			for input_name in self.linkedsets[linkedset]['inputs']:
				# input config
				dataconfs_for_input = []
				sections = task_eval_conf[input_name].split(' ')
				for section in sections:
					dataconfs_for_input.append(dict(dataconf.items(section)))
				self.input_dataconfs[linkedset].append(dataconfs_for_input)

			self.target_dataconfs[linkedset] = []
			for target_name in self.linkedsets[linkedset]['targets']:
				# target config
				dataconfs_for_target = []
				sections = task_eval_conf[target_name].split(' ')
				for section in sections:
					dataconfs_for_target.append(dict(dataconf.items(section)))
				self.target_dataconfs[linkedset].append(dataconfs_for_target)

		self.model_links = dict()
		self.inputs_links = dict()
		self.nodes_output_names = dict()
		for node in self.model_nodes:
			self.model_links[node] = task_eval_conf['%s_model' % node]
			self.inputs_links[node] = task_eval_conf['%s_inputs' % node].split(' ')
			if '%s_output_names' % node in task_eval_conf:
				self.nodes_output_names[node] = task_eval_conf['%s_output_names' % node].split(' ')
			else:
				self.nodes_output_names[node] = node

	def evaluate(self, start_utt_ind=0):
		"""evaluate the performance of the model

		Returns:
			- the loss as a scalar tensor
			- the number of batches in the validation set as an integer
		"""

		with tf.name_scope('evaluate'):
			inputs = dict()
			seq_lengths = dict()
			targets = dict()
			loss = []
			norm = []
			for set_ind, linkedset in enumerate(self.linkedsets):
				data_queue_elements, _ = input_pipeline.get_filenames(
					self.input_dataconfs[linkedset] + self.target_dataconfs[linkedset])

				max_number_of_elements = len(data_queue_elements)
				number_of_elements = min([max_number_of_elements, self.requested_utts])

				# compute the number of batches in the validation set
				numbatches = number_of_elements/self.batch_size
				number_of_elements = numbatches*self.batch_size
				if number_of_elements == 0:
					raise BaseException('The number of elements used for validation must be larger than 0.')
				print('%d utterances will be used for evaluation' % number_of_elements)

				# cut the data so it has a whole number of batches
				data_queue_elements = data_queue_elements[start_utt_ind:number_of_elements]

				# create the data queue and queue runners (inputs are not allowed to get shuffled. I already did this so set to False)
				data_queue = tf.train.string_input_producer(
					string_tensor=data_queue_elements,
					shuffle=False,
					seed=None,
					capacity=self.batch_size*2)

				# create the input pipeline
				data, seq_length = input_pipeline.input_pipeline(
					data_queue=data_queue,
					batch_size=self.batch_size,
					numbuckets=1,
					dataconfs=self.input_dataconfs[linkedset] + self.target_dataconfs[linkedset]
				)
				# split data into inputs and targets
				for ind, input_name in enumerate(self.input_names):
					inputs[input_name] = data[ind]
					seq_lengths[input_name] = seq_length[ind]

				# out_seq_lengths = {
				# 	seq_name: seq for seq_name, seq in seq_lengths.iteritems()
				# 	if seq_name in self.output_names}
				out_seq_lengths = {
					output_name: seq_lengths[self.input_names[0]] for output_name in self.output_names}

				for ind, target_name in enumerate(self.target_names):
					targets[target_name] = data[len(self.input_names)+ind]

				# get the logits
				logits = self._get_outputs(
					inputs=inputs,
					seq_lengths=seq_lengths)

				set_loss, set_norm = self.compute_loss(targets, logits, seq_lengths)
				set_loss *= self.linkedset_weighting[linkedset]
				set_norm *= self.linkedset_weighting[linkedset]
				loss.append(set_loss)
				norm.append(set_norm)
		loss = tf.reduce_sum(loss)
		norm = tf.reduce_sum(norm)

		return loss, norm, numbatches, logits, targets, out_seq_lengths

	@abstractmethod
	def _get_outputs(self, inputs, seq_length):
		"""compute the validation outputs for a batch of data

		Args:
			inputs: the inputs to the neural network, this is a list of
				[batch_size x ...] tensors
			seq_length: The sequence lengths of the input utterances, this
				is a list of [batch_size] vectors

		Returns:
			the outputs"""

	@abstractmethod
	def compute_loss(self, targets, logits, seq_length):
		"""compute the validation loss for a batch of data

		Args:
			targets: a dictionary of [batch_size x time x ...] tensor containing
				the targets
			logits: a dictionary of [batch_size x time x ...] tensor containing
				the logits
			seq_length: a dictionary of [batch_size] vectors containing
				the sequence lengths

		Returns:
			a scalar value containing the loss"""
