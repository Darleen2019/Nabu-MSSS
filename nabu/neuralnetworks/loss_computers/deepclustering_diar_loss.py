"""@file deepclustering_diar_loss.py
contains the DeepclusteringDiarLoss"""

import loss_computer
from nabu.neuralnetworks.components import ops


class DeepclusteringDiarLoss(loss_computer.LossComputer):
    """A loss computer that calculates the loss"""

    def __call__(self, targets, logits, seq_length):
        """
        Compute the loss

        Creates the operation to compute the deep clustering diarization loss

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

        vad_target = targets['diar_targets']
        seq_length = seq_length['features']
        read_heads = logits['read_heads']

        loss, norm = ops.deepclustering_diar_loss(vad_target, read_heads, seq_length, self.batch_size)

        return loss, norm
