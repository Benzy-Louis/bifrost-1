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

"""@package blocks
This file contains blocks specific to LEDA-OVRO.
"""

import os
import json
import itertools
import numpy as np
import bifrost
from bifrost.addon.leda import bandfiles
from bifrost.block import SourceBlock, MultiTransformBlock

DADA_HEADER_SIZE = 4096
LEDA_OUTRIGGERS = [252, 253, 254, 255, 256]
LEDA_NSTATIONS = 256
SPEED_OF_LIGHT = 299792458.

def cast_string_to_number(string):
    """Attempt to convert a string to integer or float"""
    try:
        return int(string)
    except ValueError:
        pass
    try:
        return float(string)
    except ValueError:
        pass
    return string

# Read a collection of DADA files and form an array of time series data over
# many frequencies.
# TODO: Add more to the header.
# Add a list of frequencies present. This could be the full band,
# but there could be gaps. Downstream functionality has to be aware of the gaps.
# Allow specification of span size based on time interval
class DadaReadBlock(SourceBlock):
    # Assemble a group of files in the time direction and the frequency direction
    # time_stamp is of the form "2016-05-24-11:04:38", or a DADA file ending in .dada
    def __init__(self, filename, core=-1, gulp_nframe=4096):
        self.CHANNEL_WIDTH = 0.024
        self.SAMPLING_RATE = 41.66666666667e-6
        self.N_CHAN = 109
        self.N_BEAM = 2
        self.HEADER_SIZE = 4096
        self.OBS_OFFSET = 1255680000
        self.gulp_nframe = gulp_nframe
        self.core = core
        beamformer_scans = []
        beamformer_scans.append(bandfiles.BandFiles(filename))  # Just one file
        # Report what we've got
        print "Num files in time:",  len(beamformer_scans)
        print "File and number:"
        for scan in beamformer_scans:
            print os.path.basename(scan.files[0].name)+":", len(scan.files)
        self.beamformer_scans = beamformer_scans         # List of full-band time steps
    def main(self, output_ring):
        bifrost.affinity.set_core(self.core)
        self.oring = output_ring
        # Calculate some constants for sizes
        length_one_second = int(round(1/self.SAMPLING_RATE))
        ring_span_size = length_one_second*self.N_CHAN*4                                        # 1 second, all the channels (109) and then 4-byte floats
        file_chunk_size = length_one_second*self.N_BEAM*self.N_CHAN*2                               # 1 second, 2 beams, 109 chans, and 2 1-byte ints (real, imag)
        number_of_seconds = 120         # Change this
        ohdr = {}
        ohdr["shape"] = (self.N_CHAN, 1)
        ohdr["frame_shape"] = ( self.N_CHAN, 1 )
        ohdr["nbit"] = 32
        ohdr["dtype"] = str(np.float32)
        ohdr["tstart"] = 0
        ohdr["tsamp"] = self.SAMPLING_RATE
        ohdr['foff'] = self.CHANNEL_WIDTH
        #print length_one_second, ring_span_size, file_chunk_size, number_of_chunks
        with self.oring.begin_writing() as oring:
            # Go through the files by time. 
            for scan in self.beamformer_scans:
                # Go through the frequencies
                for f in scan.files:
                    print "Opening", f.name
                    with open(f.name,'rb') as ifile:
                        ifile.read(self.HEADER_SIZE)
                        ohdr["cfreq"] = f.freq
                        ohdr["fch1"] = f.freq
                        self.oring.resize(ring_span_size)
                        with oring.begin_sequence(f.name, header=json.dumps(ohdr)) as osequence:
                            for i in range(number_of_seconds):
                                # Get a chunk of data from the file. The whole band is used, but only a chunk of time (1 second).
                                # Massage the data so it can go through the ring. That means changng the data type and flattening.
                                try:
                                    data = np.fromfile(ifile, count=file_chunk_size, dtype=np.int8).astype(np.float32)
                                except:
                                    print "Bad read. Stopping read."
                                    return
                                if data.size != length_one_second*self.N_BEAM*self.N_CHAN*2:
                                    print "Bad data shape. Stopping read."
                                    return
                                data = data.reshape(length_one_second, self.N_BEAM, self.N_CHAN, 2)
                                power = (data[...,0]**2 + data[...,1]**2).mean(axis=1)  # Now have time by frequency.
                                # Send the data
                                with osequence.reserve(ring_span_size) as wspan:
                                    wspan.data[0][:] = power.view(dtype=np.uint8).ravel()
class DadaFileRead(object):
    """File object for reading in a dada file
    @param[in] output_chans The frequency channels to output
    @param[in] time_steps The number of time samples to output"""
    def __init__(self, filename, output_chans, time_steps):
        super(DadaFileRead, self).__init__()
        self.filename = filename
        self.file_object = open(filename, 'rb')
        self.dada_header = {}
        self.output_chans = output_chans
        self.time_steps = time_steps
        self.framesize = {'full': 0, 'outrigger': 0}
        self.shape = []
    def parse_dada_header(self):
        """Get settings out of the dada file's header"""
        header_string = self.file_object.read(DADA_HEADER_SIZE)
        self.dada_header = {}
        for line in header_string.split('\n'):
            try:
                key, value = line.split(None, 1)
            except ValueError:
                break
            key = key.strip()
            value = value.strip()
            value = cast_string_to_number(value)
            self.dada_header[key] = value
    def interpret_header(self):
        """Generate settings based on the dada's header"""
        outrig_nbaseline = sum([LEDA_NSTATIONS-x for x in range(len(LEDA_OUTRIGGERS))])
        nchan = self.dada_header['NCHAN']
        npol = self.dada_header['NPOL']
        navg = self.dada_header['NAVG']
        frequency_channel_width = self.dada_header['BW']*1e6 / float(nchan)
        assert self.dada_header['DATA_ORDER'] == "TIME_SUBSET_CHAN_TRIANGULAR_POL_POL_COMPLEX"
        nbaseline = LEDA_NSTATIONS*(LEDA_NSTATIONS+1)//2
        noutrig_per_full = int(navg/frequency_channel_width + 0.5)
        self.framesize['full'] = nchan*nbaseline*npol*npol
        self.framesize['outrigger'] = noutrig_per_full*nchan*outrig_nbaseline*npol*npol
        self.shape = (nchan, nbaseline, npol, npol)
    def dada_read(self):
        """Read in the entirety of the dada file"""
        filesize = os.path.getsize(self.filename) - DADA_HEADER_SIZE
        tot_framesize = self.framesize['full'] + self.framesize['outrigger']
        ntime = float(filesize)/(tot_framesize*8)
        for i in range(self.time_steps):
            if i >= ntime:
                print "Stopping read of Dada file."
                break
            full_data = np.fromfile(
                self.file_object,
                dtype=np.complex64,
                count=self.framesize['full'])
            # Outrigger data is not used:
            np.fromfile(
                self.file_object,
                dtype=np.complex64,
                count=self.framesize['outrigger'])
            try:
                full_data = full_data.reshape(self.shape)
                select_channel_data = full_data[self.output_chans, :, :, :]
                yield select_channel_data
            except ValueError:
                print "Bad data reshape, possibly due to end of file"
                break

def build_baseline_ants(nant):
	nbaseline = nant*(nant+1)/2
	baseline_ants = np.empty((nbaseline,2), dtype=np.int32)
	for i in xrange(nant):
		for j in xrange(i+1):
			b = i*(i+1)/2 + j
			baseline_ants[b,0] = i
			baseline_ants[b,1] = j
	return baseline_ants

class NewDadaReadBlock(DadaFileRead, SourceBlock):
    """Read a dada file in with frequency channels in ringlets."""
    def __init__(self, filename, output_chans, time_steps):
        """@param[in] filename The dada file.
        @param[in] output_chans The frequency channels to output
        @param[in] time_steps The number of time samples to output"""
        super(NewDadaReadBlock, self).__init__(
            output_chans=output_chans,
            time_steps=time_steps,
            filename=filename)
    def main(self, output_ring):
        """Put dada file data onto output_ring
        @param[out] output_ring Ring to contain outgoing data"""
        self.parse_dada_header()
        self.interpret_header()
        nchan = self.dada_header['NCHAN']
        npol = self.dada_header['NPOL']
        nstand = LEDA_NSTATIONS
        output_shape = [
            len(self.output_chans),
            nstand,
            nstand,
            npol,
            npol]
        sizeofcomplex64 = 8
        self.gulp_size = np.product(output_shape)*sizeofcomplex64
        self.output_header = json.dumps({
            'nbit':64,
            'dtype':str(np.complex64),
            'shape':output_shape})
        for dadafile_data, output_span in itertools.izip(
                self.dada_read(),
                self.iterate_ring_write(output_ring)):
            data = np.empty(output_shape, dtype=np.complex64)
            baseline_ants = build_baseline_ants(nstand)
            ants_i = baseline_ants[:,0]
            ants_j = baseline_ants[:,1]
            data[:,ants_i,ants_j,:,:] = dadafile_data
            data[:,ants_j,ants_i,:,:] = dadafile_data.conj()
            output_span.data_view(np.complex64)[0][:] = data.ravel()
        self.file_object.close()

class CableDelayBlock(MultiTransformBlock):
    """Apply cable delays to a visibility matrix"""
    ring_names = {
        'in': "Visibilities WITHOUT cable delays added",
        'out': "Visibilities WITH cable delays added"}
    def __init__(self, frequencies, delays, dispersions):
        """@param[in] frequencies Frequencies of data in (Hz)
        @param[in] delays Delays for each antenna (s)
        @param[in] dispersions Dispersion for each antenna (?)"""
        super(CableDelayBlock, self).__init__()
        self.cable_delay_matrix = self.calculate_cable_delay_matrix(
            frequencies,
            delays,
            dispersions)
    def calculate_cable_delay_matrix(self, frequencies, delays, dispersions):
        """Calculate the cable delays,
            then build a matrix to apply to the visibilities"""
        cable_delays = (delays+dispersions)/np.sqrt(frequencies)*SPEED_OF_LIGHT*0.82
        cable_delay_weights = np.exp(1j*2*np.pi*cable_delays/SPEED_OF_LIGHT*frequencies)
        return cable_delay_weights.astype(np.complex64)
    def load_settings(self):
        """Gulp data appropriately to the shape of the input"""
        sizeofcomplex64 = 8
        self.gulp_size['in'] = np.product(self.header['in']['shape'])*sizeofcomplex64
        self.header['out'] = self.header['in']
        self.gulp_size['out'] = self.gulp_size['in']
    def main(self):
        """Apply the cable delays to the output matrix"""
        for inspan, outspan in self.izip(self.read('in'), self.write('out')):
            #print inspan.view(np.complex64).shape, np.product(self.header['in']['shape'])
            visibilities = np.copy(inspan.view(np.complex64).reshape(self.header['in']['shape']))
            for i in range(self.header['in']['shape'][1]):
                for j in range(self.header['in']['shape'][1]):
                    visibilities[0, i, j, 0, 0] *= self.cable_delay_matrix[i, 0]
                    visibilities[0, i, j, 0, 0] *= self.cable_delay_matrix[j, 0].conj()
                    visibilities[0, i, j, 1, 1] *= self.cable_delay_matrix[i, 1]
                    visibilities[0, i, j, 1, 1] *= self.cable_delay_matrix[j, 1].conj()
            """
            visibilities[...,0,0] *= self.cable_delay_matrix[:,None,:,0].conj()
            visibilities[...,1,1] *= self.cable_delay_matrix[:,None,:,1].conj()
            visibilities[...,0,0] *= self.cable_delay_matrix[:,:,None,0]
            visibilities[...,1,1] *= self.cable_delay_matrix[:,:,None,1]
            """
            outspan[:] = visibilities.ravel().view(np.float32)[:]
