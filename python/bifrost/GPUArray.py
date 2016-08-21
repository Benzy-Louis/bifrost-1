
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

import ctypes
import numpy as np
from memory import raw_malloc, raw_free, memset, memcpy, memcpy2D
from bifrost.libbifrost import _bf


class GPUArray(object):
	def __init__(self, shape, dtype, buffer=None, offset=0, strides=None):
		itemsize = dtype().itemsize
                shape = tuple(np.array(shape).ravel().astype(np.uint64))
		if strides is None:
			# This magic came from http://stackoverflow.com/a/32874295
			strides = itemsize*np.r_[1,np.cumprod(shape[::-1][:-1])][::-1]
                #Convert back to prevent JSON error from numpy datatype
                shape = tuple(int(shape[i]) for i in range(len(shape)))
		self.shape   = shape
		self._dtype   = dtype
		self.buffer  = buffer
		self.offset  = offset
		self.strides = strides
		self.base    = None
		self.flags   = {'WRITEABLE':    True,
		                'ALIGNED':      buffer%itemsize==0 if buffer is not None else True,
		                'OWNDATA':      False,
		                'UPDATEIFCOPY': False,
		                'C_CONTIGUOUS': self.nbytes==strides[0]*shape[0],
		                'F_CONTIGUOUS': False,
		                'SPACE':        'cuda'}
		class CTypes(object):
			def __init__(self, parent):
				self.parent = parent
			@property
			def data(self):
				return self.parent.data
		self.ctypes = CTypes(self)
		if self.buffer is None:
			self.buffer = raw_malloc(self.nbytes, space='cuda')
			self.flags['OWNDATA'] = True
			self.flags['ALIGNED'] = True
			memset(self, 0)
		else:
			self.buffer += offset
	def __del__(self):
		if self.flags['OWNDATA']:
			raw_free(self.buffer, self.flags['SPACE'])
        @property
        def dtype(self):
            return np.dtype(self._dtype)
	@property
	def data(self):
		return self.buffer
	#def reshape(self, shape):
	#	# TODO: How to deal with strides?
	#	#         May be non-contiguous but the reshape still works
	#	#           E.g., splitting dims
	#	return GPUArray(shape, self.dtype,
	#	                buffer=self.buffer,
	#	                offset=self.offset,
	#	                strides=self.strides)
	@property
	def size(self):
		return int(np.prod(self.shape))
	@property
	def itemsize(self):
		return self._dtype().itemsize
	@property
	def nbytes(self):
		return self.size*self.itemsize
	@property
	def ndim(self):
		return len(self.shape)
	def get(self, dst=None):
		hdata = dst if dst is not None else np.empty(self.shape, self._dtype)
		assert(hdata.shape == self.shape)
		assert(hdata.dtype == self._dtype)
		if self.flags['C_CONTIGUOUS'] and hdata.flags['C_CONTIGUOUS']:
			memcpy(hdata, self)
		elif self.ndim == 2:
			memcpy2D(hdata, self)
		else:
			raise RuntimeError("Copying with this data layout is unsupported")
		return hdata
	def set(self, hdata):
		assert(hdata.shape == self.shape)
		hdata = hdata.astype(self._dtype)
		if self.flags['C_CONTIGUOUS'] and hdata.flags['C_CONTIGUOUS']:
			memcpy(self, hdata)
		elif self.ndim == 2:
			memcpy2D(self, hdata)
		else:
			raise RuntimeError("Copying with this data layout is unsupported")
		return self
        def as_BFarray(self, bf_max_dimensions=100):
                data_void_pointer = ctypes.cast(
                    self.buffer, ctypes.c_void_p)
                cuda_space = 2
                #nelements = np.zeros(
                #    shape=bf_max_dimensions)
                #nelements[:len(self.shape)] += self.shape
                #nelements = nelements.ctypes.data_as(
                #    ctypes.c_ulong*bf_max_dimensions)
                shape = self.shape
                shape = (_bf.BFsize*bf_max_dimensions)(*list(shape))
                #nelements = 
                    #(ctypes.c_uint64*bf_max_dimensions)(*
                #TODO: Fix this test code
                strides = (_bf.BFsize*bf_max_dimensions)(*list(shape))
                #dtype = _bf.BFsize(1)
                ndim = len(self.shape)
                BFarray = _bf.BFarray(
                    data_void_pointer, cuda_space,
                    1, ndim,
                    shape, strides)
                return BFarray
        def as_BFconstarray(self, bf_max_dimensions=100):
                data_void_pointer = ctypes.cast(
                    self.buffer, ctypes.c_void_p)
                cuda_space = 2
                #nelements = np.zeros(
                #    shape=bf_max_dimensions)
                #nelements[:len(self.shape)] += self.shape
                #nelements = nelements.ctypes.data_as(
                #    ctypes.c_ulong*bf_max_dimensions)
                shape = self.shape
                shape = (_bf.BFsize*bf_max_dimensions)(*list(shape))
                #nelements = 
                    #(ctypes.c_uint64*bf_max_dimensions)(*
                #TODO: Fix this test code
                strides = (_bf.BFsize*bf_max_dimensions)(*list(shape))
                #dtype = _bf.BFsize(1)
                ndim = len(self.shape)
                BFarray = _bf.BFconstarray(
                    data_void_pointer, cuda_space,
                    1, ndim,
                    shape, strides)
                return BFarray
