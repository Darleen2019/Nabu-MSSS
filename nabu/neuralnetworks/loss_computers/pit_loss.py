"""@file pit_loss.py
contains the PITLoss"""

import loss_computer
from nabu.neuralnetworks.components import ops
import tensorflow as tf


class PITLoss(loss_computer.LossComputer):
	"""A loss computer that calculates the loss"""

	def __call__(self, targets, logits, seq_length):
		"""
		Compute the loss

		Creates the operation to compute the Permudation Invariant Training loss

		Args:
			targets: a dictionary of [batch_size x time x ...] tensor containing
				the targets
			logits: a dictionary of [batch_size x time x ...] tensors containing the logits
			seq_length: a dictionary of [batch_size] vectors containing
				the sequence lengths

		Returns:
			loss: a scalar value containing the loss
			norm: a scalar value indicating how to normalize the loss
		"""

		multi_targets = targets['multi_targets']
		mix_to_mask = targets['mix_to_mask']
		seq_length = seq_length['bin_est']
		logits = logits['bin_est']

		loss, norm = ops.pit_loss(multi_targets, logits, mix_to_mask, seq_length, self.batch_size, activation='softmax')
			
		return loss, norm
	
	
class PITLossSigmoid(loss_computer.LossComputer):
	"""A loss computer that calculates the loss"""
	
	def __call__(self, targets, logits, seq_length):
		"""
		Compute the loss
	
		Creates the operation to compute the Permudation Invariant Training loss
	
		Args:
			targets: a dictionary of [batch_size x time x ...] tensor containing
				the targets
			logits: a dictionary of [batch_size x time x ...] tensors containing the logits
			seq_length: a dictionary of [batch_size] vectors containing
				the sequence lengths
	
		Returns:
			loss: a scalar value containing the loss
			norm: a scalar value indicating how to normalize the loss
		"""

		multi_targets = targets['multi_targets']
		mix_to_mask = targets['mix_to_mask']
		seq_length = seq_length['bin_est']
		logits = logits['bin_est']

		loss, norm = ops.pit_loss(multi_targets, logits, mix_to_mask, seq_length, self.batch_size, activation='sigmoid')

		return loss, norm


class PITLossSigmoidScaled(loss_computer.LossComputer):
	"""A loss computer that calculates the loss"""

	def __call__(self, targets, logits, seq_length):
		"""
		Compute the loss

		Creates the operation to compute the Permudation Invariant Training loss

		Args:
			targets: a dictionary of [batch_size x time x ...] tensor containing
				the targets
			logits: a dictionary of [batch_size x time x ...] tensors containing the logits
			seq_length: a dictionary of [batch_size] vectors containing
				the sequence lengths

		Returns:
			loss: a scalar value containing the loss
			norm: a scalar value indicating how to normalize the loss
		"""

		multi_targets = targets['multi_targets']
		mix_to_mask = targets['mix_to_mask']
		seq_length = seq_length['bin_est']
		logits = logits['bin_est']

		loss, norm = ops.pit_loss(
			multi_targets, logits, mix_to_mask, seq_length, self.batch_size, activation='sigmoid', rescale_recs=True)

		return loss, norm


class PITLossOverspeakerized(loss_computer.LossComputer):
	"""A loss computer that calculates the loss"""

	def __call__(self, targets, logits, seq_length):
		"""
		Compute the loss

		Creates the operation to compute the Permudation Invariant Training loss

		Args:
			targets: a dictionary of [batch_size x time x ...] tensor containing
				the targets
			logits: a dictionary of [nrS x batch_size x time x ...] tensors containing the logits
			seq_length: a dictionary of [batch_size] vectors containing
				the sequence lengths

		Returns:
			loss: a scalar value containing the loss
			norm: a scalar value indicating how to normalize the loss
		"""

		multi_targets = targets['multi_targets']
		mix_to_mask = targets['mix_to_mask']
		seq_length = seq_length['bin_est']
		logits = logits['bin_est']

		print 'Assuming "bin_est" is already activated with sigmoid'

		loss, norm = ops.pit_loss(
			multi_targets, logits, mix_to_mask, seq_length, self.batch_size, activation=None, rescale_recs=False,
			overspeakerized=True)

		return loss, norm

