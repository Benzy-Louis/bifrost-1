
# Copyright (c) 2016, The Bifrost Authors. All rights reserved.
# Copyright (c) 2016, NVIDIA CORPORATION. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of The Bifrost Authors nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from pipeline import TransformBlock
import bifrost as bf
import bifrost.transpose

from copy import deepcopy

class TransposeBlock(TransformBlock):
	def __init__(self, iring, axes, *args, **kwargs):
		super(TransposeBlock, self).__init__([iring], *args, **kwargs)
		self.axes = axes
		self.space = self.orings[0].space
	def on_sequence(self, iseqs):
		iseq = iseqs[0]
		ihdr = iseq.header
		itensor = ihdr['_tensor']
		# TODO: Is this a good idea?
		#if self.axes is None:
		#	# Default to moving the time axis to/from the fastest dim
		#	naxis     = len(itensor['shape'])
		#	time_axis = itensor['shape'].index(-1)
		#	self.axes = range(time_axis) + range(time_axis+1,naxis)
		#	if time_axis == 0: # Time was slowest dim
		#		self.axes += [-1] # Make time the fastest dim
		#	else: # Time was not the slowest dim
		#		self.axes = [-1] + self.axes # Make time the slowest dim
		for d in xrange(len(self.axes)):
			if isinstance(self.axes[d], basestring):
				# Look up axis by label
				self.axes[d] = itensor['labels'].index(self.axes[d])
		ohdr = deepcopy(ihdr)
		# Permute metadata of axes
		for item in ['shape', 'labels', 'scales', 'units']:
			ohdr['_tensor'][item] = [itensor[item][axis]
			                         for axis in self.axes]
		return [ohdr], [None]
	def on_data(self, ispans, ospans):
		# TODO: bf.memory.transpose should support system space too
		if bf.memory.space_accessible(self.space, ['cuda']):
			bf.transpose.transpose(ospans[0].data, ispans[0].data, self.axes)
		else:
			ospans[0].data[...] = np.transpose(ispans[0].data, self.axes)

def transpose(iring, axes, *args, **kwargs):
	return TransposeBlock(iring, axes, *args, **kwargs)
