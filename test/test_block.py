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

"""@package test_block
This file tests all aspects of the Bifrost.block module.
"""
import unittest
from bifrost.block import *
from bifrost.ring import Ring

class TestTestingBlock(unittest.TestCase):
    """Test the TestingBlock for basic functionality"""
    def test_simple_dump(self):
        """Input some numbers, and ensure they are written to a file"""
        blocks = []
        blocks.append((TestingBlock([1, 2, 3]), [], [0]))
        blocks.append((WriteAsciiBlock('.log.txt', gulp_size=3*4), [0], []))
        Pipeline(blocks).main()
        dumped_numbers = np.loadtxt('.log.txt')
        np.testing.assert_almost_equal(dumped_numbers, [1, 2, 3])
    def test_multi_dimensional_input(self):
        """Input a 2 dimensional list, and have this printed"""
        blocks = []
        test_array = [[1, 2], [3, 4]]
        blocks.append((TestingBlock(test_array), [], [0]))
        blocks.append((WriteAsciiBlock('.log.txt', gulp_size=4*4), [0], []))
        blocks.append((WriteHeaderBlock('.log2.txt'), [0], []))
        Pipeline(blocks).main()
        header = eval(open('.log2.txt').read())
        dumped_numbers = np.loadtxt('.log.txt').reshape(header['shape'])
        np.testing.assert_almost_equal(dumped_numbers, test_array)
class TestCopyBlock(unittest.TestCase):
    """Performs tests of the Copy Block."""
    def setUp(self):
        """Set up the blocks list, and put in a single
            block which reads in the data from a filterbank
            file."""
        self.blocks = []
        self.blocks.append((
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/1chan8bitNoDM.fil'),
            [], [0]))
    def test_simple_copy(self):
        """Test which performs a read of a sigproc file,
            copy to one ring, and then output as text."""
        logfile = '.log.txt'
        self.blocks.append((CopyBlock(), [0], [1]))
        self.blocks.append((WriteAsciiBlock(logfile), [1], []))
        Pipeline(self.blocks).main()
        test_byte = open(logfile, 'r').read(1)
        self.assertEqual(test_byte, '2')
    def test_multi_copy(self):
        """Test which performs a read of a sigproc file,
            copy between many rings, and then output as
            text."""
        logfile = '.log.txt'
        for i in range(10):
            self.blocks.append(
                (CopyBlock(), [i], [i+1]))
        self.blocks.append((WriteAsciiBlock(logfile), [10], []))
        Pipeline(self.blocks).main()
        test_byte = open(logfile, 'r').read(1)
        self.assertEqual(test_byte, '2')
    def test_non_linear_multi_copy(self):
        """Test which reads in a sigproc file, and
            loads it between different rings in a
            nonlinear fashion, then outputs to file."""
        logfile = '.log.txt'
        self.blocks.append((CopyBlock(), [0], [1]))
        self.blocks.append((CopyBlock(), [0], [2]))
        self.blocks.append((CopyBlock(), [2], [5]))
        self.blocks.append((CopyBlock(), [0], [3]))
        self.blocks.append((CopyBlock(), [3], [4]))
        self.blocks.append((CopyBlock(), [5], [6]))
        self.blocks.append((WriteAsciiBlock(logfile), [6], []))
        Pipeline(self.blocks).main()
        log_nums = open(logfile, 'r').read(500).split(' ')
        test_num = np.float(log_nums[8])
        self.assertEqual(test_num, 3)
    def test_single_block_multi_copy(self):
        """Test which forces one block to do multiple
            copies at once, and then dumps to two files,
            checking them both."""
        logfiles = ['.log1.txt', '.log2.txt']
        self.blocks.append((CopyBlock(), [0], [1, 2]))
        self.blocks.append((WriteAsciiBlock(logfiles[0]), [1], []))
        self.blocks.append((WriteAsciiBlock(logfiles[1]), [2], []))
        Pipeline(self.blocks).main()
        test_bytes = int(
            open(logfiles[0], 'r').read(1)) + int(
                open(logfiles[1], 'r').read(1))
        self.assertEqual(test_bytes, 4)
    def test_32bit_copy(self):
        """Perform a simple test to confirm that 32 bit
            copying has no information loss"""
        logfile = '.log.txt'
        self.blocks = []
        self.blocks.append((
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/256chan32bitNoDM.fil'),
            [], [0]))
        self.blocks.append((CopyBlock(), [0], [1]))
        self.blocks.append((WriteAsciiBlock(logfile), [1], []))
        Pipeline(self.blocks).main()
        test_bytes = open(logfile, 'r').read(500).split(' ')
        self.assertAlmostEqual(np.float(test_bytes[0]), 0.72650784254)

class TestFoldBlock(unittest.TestCase):
    """This tests functionality of the FoldBlock."""
    def setUp(self):
        """Set up the blocks list, and put in a single
            block which reads in the data from a filterbank
            file."""
        self.blocks = []
        self.blocks.append((
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/pulsar_noisey_NoDM.fil'),
            [], [0]))
    def dump_ring_and_read(self):
        """Dump block to ring, read in as histogram"""
        logfile = ".log.txt"
        self.blocks.append((WriteAsciiBlock(logfile), [1], []))
        Pipeline(self.blocks).main()
        test_bytes = open(logfile, 'r').read().split(' ')
        histogram = np.array([np.float(x) for x in test_bytes])
        return histogram
    def test_simple_pulsar(self):
        """Test whether a pulsar histogram
            shows a large peak and is mostly
            nonzero values"""
        self.blocks.append((
            FoldBlock(bins=100), [0], [1]))
        histogram = self.dump_ring_and_read()
        self.assertEqual(histogram.size, 100)
        self.assertTrue(np.min(histogram) > 1e-10)
    def test_different_bin_size(self):
        """Try a different bin size"""
        self.blocks.append((
            FoldBlock(bins=50), [0], [1]))
        histogram = self.dump_ring_and_read()
        self.assertEqual(histogram.size, 50)
    def test_show_pulse(self):
        self.blocks[0] = (
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/simple_pulsar_DM0.fil'),
            [], [0])
        """Test to see if a pulse is visible in the
            histogram from pulsar data"""
        self.blocks.append((
            FoldBlock(bins=200), [0], [1]))
        histogram = self.dump_ring_and_read()
        self.assertTrue(np.min(histogram) > 1e-10)
        self.assertGreater(
            np.max(histogram)/np.average(histogram), 5)
    def test_many_channels(self):
        """See if many channels work with folding"""
        self.blocks[0] = (
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/simple_pulsar_DM0_128ch.fil'),
            [], [0])
        self.blocks.append((
            FoldBlock(bins=200), [0], [1]))
        histogram = self.dump_ring_and_read()
        self.assertTrue(np.min(histogram) > 1e-10)
        self.assertGreater(
            np.max(histogram)/np.min(histogram), 3)
    def test_high_DM(self):
        """Test folding on a file with high DM"""
        self.blocks[0] = (
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/simple_pulsar_DM10_128ch.fil'),
            [], [0])
        self.blocks.append((
            FoldBlock(bins=200, dispersion_measure=10, core=0),
            [0], [1]))
        histogram = self.dump_ring_and_read()
        self.assertTrue(np.min(histogram) > 1e-10)
        self.assertGreater(
            np.max(histogram)/np.min(histogram), 3)
        #TODO: Test to break bfmemcpy2D for lack of float32 functionality?
class TestKurtosisBlock(unittest.TestCase):
    """This tests functionality of the KurtosisBlock."""
    def test_data_throughput(self):
        """Check that data is being put through the block
        (does this by checking consistency of shape/datatype)"""
        blocks = []
        blocks.append((
            SigprocReadBlock('/data1/mcranmer/data/fake/1chan8bitNoDM.fil'),
            [], [0]))
        blocks.append((
            KurtosisBlock(), [0], [1]))
        blocks.append((
            WriteAsciiBlock('.log.txt'), [1], []))
        Pipeline(blocks).main()
        test_byte = open('.log.txt', 'r').read().split(' ')
        test_nums = np.array([float(x) for x in test_byte])
        self.assertLess(np.max(test_nums), 256)
        self.assertEqual(test_nums.size, 4096)
class TestFFTBlock(unittest.TestCase):
    """This test assures basic functionality of fft block"""
    def setUp(self):
        """Assemble a basic pipeline with the FFT block"""
        self.logfile = '.log.txt'
        self.blocks = []
        self.blocks.append((
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/1chan8bitNoDM.fil'),
            [], [0]))
        self.blocks.append((FFTBlock(gulp_size=4096*8*8*8), [0], [1]))
        self.blocks.append((WriteAsciiBlock(self.logfile), [1], []))
    def test_throughput(self):
        """Test that any data is being put through"""
        Pipeline(self.blocks).main()
        test_string = open(self.logfile, 'r').read()
        self.assertGreater(len(test_string), 0)
    def test_throughput_size(self):
        """Number of elements going out should be double that of basic copy"""
        Pipeline(self.blocks).main()
        number_fftd = len(open(self.logfile, 'r').read().split(' '))
        open(self.logfile, 'w').close()
        ## Run pipeline again with simple copy
        self.blocks[1] = (CopyBlock(), [0], [1])
        Pipeline(self.blocks).main()
        #number_copied = len(open(self.logfile, 'r').read().split(' '))
        #self.assertEqual(number_fftd, 2*number_copied)
    def test_data_sizes(self):
        """Test that different number of bits give correct throughput size"""
        for iterate in range(5):
            nbit = 2**iterate
            if nbit == 8:
                continue
            self.blocks[0] = (
                SigprocReadBlock(
                    '/data1/mcranmer/data/fake/2chan'+ str(nbit) + 'bitNoDM.fil'),
                [], [0])
            open(self.logfile, 'w').close()
            Pipeline(self.blocks).main()
            number_fftd = np.loadtxt(self.logfile).astype(np.float32).view(np.complex64).size
            # Compare with simple copy
            self.blocks[1] = (CopyBlock(), [0], [1])
            open(self.logfile, 'w').close()
            Pipeline(self.blocks).main()
            number_copied = np.loadtxt(self.logfile).size
            self.assertEqual(number_fftd, number_copied)
            # Go back to FFT
            self.blocks[1] = (FFTBlock(gulp_size=4096*8*8*8), [0], [1])
    def test_fft_result(self):
        """Make sure that fft matches what it should!"""
        open(self.logfile, 'w').close()
        Pipeline(self.blocks).main()
        fft_block_result = np.loadtxt(self.logfile).astype(np.float32).view(np.complex64)
        self.blocks[1] = (CopyBlock(), [0], [1])
        open(self.logfile, 'w').close()
        Pipeline(self.blocks).main()
        normal_fft_result = np.fft.fft(np.loadtxt(self.logfile))
        np.testing.assert_almost_equal(fft_block_result, normal_fft_result, 2)
class TestIFFTBlock(unittest.TestCase):
    """This test assures basic functionality of the ifft block.
    Requires the FFT block for testing."""
    def setUp(self):
        """Assemble a basic pipeline with the FFT/IFFT blocks"""
        self.logfile = '.log.txt'
        self.blocks = []
        self.blocks.append((
            SigprocReadBlock(
                '/data1/mcranmer/data/fake/1chan8bitNoDM.fil'),
            [], [0]))
        self.blocks.append((FFTBlock(gulp_size=4096*8*8*8*8), [0], [1]))
        self.blocks.append((IFFTBlock(gulp_size=4096*8*8*8*8), [1], [2]))
        self.blocks.append((WriteAsciiBlock(self.logfile), [2], []))
    def test_equivalent_data_to_copy(self):
        """Test that the data coming out of this pipeline is equivalent
        the initial read data"""
        open(self.logfile, 'w').close()
        Pipeline(self.blocks).main()
        unfft_result = np.loadtxt(self.logfile).astype(np.float32).view(np.complex64)
        self.blocks[1] = (CopyBlock(), [0], [1])
        self.blocks[2] = (WriteAsciiBlock(self.logfile), [1], [])
        del self.blocks[3]
        open(self.logfile, 'w').close()
        Pipeline(self.blocks).main()
        untouched_result = np.loadtxt(self.logfile).astype(np.float32)
        np.testing.assert_almost_equal(unfft_result, untouched_result, 2)
class TestFakeVisBlock(unittest.TestCase):
    """Performs tests of the fake visibility Block."""
    def setUp(self):
        self.datafile_name = "/data1/mcranmer/data/fake/mona_uvw.dat"
        self.blocks = []
        self.blocks.append(
            (FakeVisBlock(self.datafile_name), [], [0]))
        self.blocks.append((WriteAsciiBlock('.log.txt'), [0], []))
    def test_output_size(self):
        """Make sure the outputs are being sized appropriate to the file"""
        Pipeline(self.blocks).main()
        # Number of uvw values:
        length_ring_buffer = len(open('.log.txt', 'r').read().split(' '))
        length_data_file = sum(1 for line in open(self.datafile_name, 'r'))
        self.assertAlmostEqual(length_ring_buffer, 4*length_data_file, -2)
    def test_valid_output(self):
        """Make sure that the numbers in the ring match the uvw data"""
        Pipeline(self.blocks).main()
        ring_buffer_10th_u_coord = open('.log.txt', 'r').read().split(' ')[9*4]
        line_count = 0
        for line in open(self.datafile_name, 'r'):
            line_count += 1
            if line_count == 10:
                data_file_10th_line = line
                break
        data_file_10th_u_coord = data_file_10th_line.split(' ')[3]
        self.assertAlmostEqual(
            float(ring_buffer_10th_u_coord),
            float(data_file_10th_u_coord),
            3)
    def test_different_size_data(self):
        """Assert that different data sizes are processed properly"""
        datafile_name = "/data1/mcranmer/data/fake/mona_uvw_half.dat"
        self.blocks[0] = (FakeVisBlock(datafile_name), [], [0])
        Pipeline(self.blocks).main()
        length_ring_buffer = len(open('.log.txt', 'r').read().split(' '))
        length_data_file = sum(1 for line in open(datafile_name, 'r'))
        self.assertAlmostEqual(length_ring_buffer, 4*length_data_file, -2)
class TestNearestNeighborGriddingBlock(unittest.TestCase):
    """Test the functionality of the nearest neighbor gridding block"""
    def setUp(self):
        """Run a pipeline on a fake visibility set and grid it"""
        self.datafile_name = "/data1/mcranmer/data/fake/mona_uvw.dat"
        self.blocks = []
        self.blocks.append((FakeVisBlock(self.datafile_name), [], [0]))
        self.blocks.append((NearestNeighborGriddingBlock(shape=(100, 100)), [0], [1]))
        self.blocks.append((WriteAsciiBlock('.log.txt'), [1], []))
    def test_output_size(self):
        """Make sure that 10,000 grid points are created"""
        Pipeline(self.blocks).main()
        grid = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        self.assertEqual(grid.size, 10000)
    def test_same_magnitude(self):
        Pipeline(self.blocks).main()
        grid = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        magnitudes = np.abs(grid)
        self.assertGreater(magnitudes[magnitudes > 0.1].size, 100)
    def test_makes_image(self):
        """Make sure that the grid can be IFFT'd into a non-gaussian image"""
        self.blocks[1] = (NearestNeighborGriddingBlock(shape=(512, 512)), [0], [1])
        Pipeline(self.blocks).main()
        grid = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        grid = grid.reshape((512, 512))
        image = np.real(np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(grid))))
        #calculate histogram of image
        histogram = np.histogram(image.ravel(), bins=100)[0]
        #check if it is gaussian (and therefore probably just noise)
        from scipy.stats import normaltest
        probability_normal = normaltest(histogram)[1]
        self.assertLess(probability_normal, 1e-2)
class TestIFFT2Block(unittest.TestCase):
    """Test the functionality of the 2D inverse fourier transform block"""
    def setUp(self):
        """Run a pipeline on a fake visibility set and IFFT it after gridding"""
        self.datafile_name = "/data1/mcranmer/data/fake/mona_uvw.dat"
        self.blocks = []
        self.blocks.append((FakeVisBlock(self.datafile_name), [], [0]))
        self.blocks.append((NearestNeighborGriddingBlock(shape=(100, 100)), [0], [1]))
        self.blocks.append((IFFT2Block(), [1], [2]))
        self.blocks.append((WriteAsciiBlock('.log.txt'), [2], []))
    def test_output_size(self):
        """Make sure that the output is the same size as the input
        The input size should be coming from the shape on the nearest neighbor"""
        open('.log.txt', 'w').close()
        Pipeline(self.blocks).main()
        brightness = np.real(np.loadtxt('.log.txt').astype(np.float32).view(np.complex64))
        self.assertEqual(brightness.size, 10000)
    def test_same_magnitude(self):
        """Make sure that many points are nonzero"""
        open('.log.txt', 'w').close()
        Pipeline(self.blocks).main()
        brightness = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        magnitudes = np.abs(brightness)
        self.assertGreater(magnitudes[magnitudes > 0.1].size, 100)
    def test_ifft_correct_values(self):
        """Make sure the IFFT produces values as if we were to do it without the block"""
        open('.log.txt', 'w').close()
        Pipeline(self.blocks).main()
        test_brightness = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        test_brightness = test_brightness.reshape((100, 100))
        self.blocks[2] = (WriteAsciiBlock('.log.txt'), [1], [])
        del self.blocks[3]
        open('.log.txt', 'w').close()
        Pipeline(self.blocks).main()
        grid = np.loadtxt('.log.txt').astype(np.float32).view(np.complex64)
        grid = grid.reshape((100, 100))
        brightness = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(grid)))
        from matplotlib import pyplot as plt
        plt.imshow(np.real(test_brightness)) #Needs to be in row,col order
        plt.savefig('mona.png')
        np.testing.assert_almost_equal(test_brightness, brightness, 2)
