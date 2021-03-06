/*
 * Copyright (c) 2016, The Bifrost Authors. All rights reserved.
 * Copyright (c) 2016, NVIDIA CORPORATION. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * * Redistributions of source code must retain the above copyright
 *   notice, this list of conditions and the following disclaimer.
 * * Redistributions in binary form must reproduce the above copyright
 *   notice, this list of conditions and the following disclaimer in the
 *   documentation and/or other materials provided with the distribution.
 * * Neither the name of The Bifrost Authors nor the names of its
 *   contributors may be used to endorse or promote products derived
 *   from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
 * OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <bifrost/array.h>
#include "assert.hpp"
#include "utils.hpp"

#include <cassert>
#include <cstring>

/*
const char* dtype2ctype_string(BFdtype dtype) {
	switch( dtype ) {
	case BF_DTYPE_I8:    return "signed char";
	case BF_DTYPE_I16:   return "short";
	case BF_DTYPE_I32:   return "int";
	case BF_DTYPE_I64:   return "long long";
	case BF_DTYPE_U8:    return "unsigned char";
	case BF_DTYPE_U16:   return "unsigned short";
	case BF_DTYPE_U32:   return "unsigned int";
	case BF_DTYPE_U64:   return "unsigned long long";
	case BF_DTYPE_F32:   return "float";
	case BF_DTYPE_F64:   return "double";
	case BF_DTYPE_F128:  return "long double";
	case BF_DTYPE_CI8:   return "complex<signed char>";
	case BF_DTYPE_CI16:  return "complex<short>";
	case BF_DTYPE_CI32:  return "complex<int>";
	case BF_DTYPE_CI64:  return "complex<long long>";
	case BF_DTYPE_CF32:  return "complex<float>";
	case BF_DTYPE_CF64:  return "complex<double>";
	case BF_DTYPE_CF128: return "complex<long double>";
	default: return 0;
	}
}
*/
// Reads array->(space,dtype,ndim,shape), sets array->strides and
//   allocates array->data.
BFstatus bfArrayMalloc(BFarray* array) {
	BF_ASSERT(array, BF_STATUS_INVALID_POINTER);
	int d = array->ndim - 1;
	array->strides[d] = get_dtype_nbyte(array->dtype);
	for( ; d-->0; ) {
		array->strides[d] = array->strides[d+1] * array->shape[d+1];
	}
	BFsize size = array->strides[0] * array->shape[0];
	return bfMalloc(&array->data, size, array->space);
}

BFstatus bfArrayFree(const BFarray* array) {
	BF_ASSERT(array, BF_STATUS_INVALID_POINTER);
	BFstatus ret = bfFree(array->data, array->space);
	//array->data = 0;
	return ret;
}

BFstatus bfArrayCopy(const BFarray* dst,
                     const BFarray* src) {
	BF_ASSERT(dst, BF_STATUS_INVALID_POINTER);
	BF_ASSERT(src, BF_STATUS_INVALID_POINTER);
	BF_ASSERT(shapes_equal(dst, src),   BF_STATUS_INVALID_SHAPE);
	BF_ASSERT(dst->dtype == src->dtype, BF_STATUS_INVALID_DTYPE);
	
	// Try squeezing contiguous dims together to reduce memory layout complexity
	BFarray dst_squeezed, src_squeezed;
	squeeze_contiguous_dims(dst, &dst_squeezed);
	squeeze_contiguous_dims(src, &src_squeezed);
	if( shapes_equal(&dst_squeezed, &src_squeezed) ) {
		dst = &dst_squeezed;
		src = &src_squeezed;
	}
	
	int ndim = dst->ndim;
	long const* shape = &dst->shape[0];
	
	if( is_contiguous(src) && is_contiguous(dst) ) {
		long size_bytes = dst->strides[0] * dst->shape[0];
		return bfMemcpy(dst->data, dst->space,
		                src->data, src->space,
		                size_bytes);
	} else if( ndim == 1 || ndim == 2 ) {
		long itemsize_bytes = BF_DTYPE_NBYTE(src->dtype);
		long width_bytes = (ndim == 2 ? shape[1] : 1) * itemsize_bytes;
		return bfMemcpy2D(dst->data, dst->strides[0], dst->space,
		                  src->data, src->strides[0], src->space,
		                  width_bytes, shape[0]);
	} else {
		BF_FAIL("Supported bfArrayCopy array layout", BF_STATUS_UNSUPPORTED); // TODO: Should support the general case
	}
}
BFstatus bfArrayMemset(const BFarray* dst,
                       int            value) {
	BF_ASSERT(dst, BF_STATUS_INVALID_POINTER);
	BF_ASSERT((unsigned char)(value) == value, BF_STATUS_INVALID_ARGUMENT);
	
	// Squeeze contiguous dims together to reduce memory layout complexity
	BFarray dst_squeezed;
	squeeze_contiguous_dims(dst, &dst_squeezed);
	dst = &dst_squeezed;
	
	int ndim = dst->ndim;
	long const* shape = &dst->shape[0];
	
	if( is_contiguous(dst) ) {
		long size_bytes = dst->strides[0] * dst->shape[0];
		return bfMemset(dst->data, dst->space,
		                value, size_bytes);
	} else if( ndim == 1 || ndim == 2 ) {
		long itemsize_bytes = BF_DTYPE_NBYTE(dst->dtype);
		long width_bytes = (ndim == 2 ? shape[1] : 1) * itemsize_bytes;
		return bfMemset2D(dst->data, dst->strides[0], dst->space,
		                  value, width_bytes, shape[0]);
	} else {
		BF_FAIL("Supported bfArrayMemset array layout", BF_STATUS_UNSUPPORTED); // TODO: Should support the general case
	}
}

