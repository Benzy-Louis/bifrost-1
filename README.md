# Bifrost 

| **`GPU+CPU`** | **`CPU-only`** | 
|-----------------|----------------------|
| [![Jenkins](https://img.shields.io/travis/rust-lang/rust.svg)]() | [![Travis](https://travis-ci.org/ledatelescope/bifrost.svg?branch=master)](https://travis-ci.org/ledatelescope/bifrost) |

A stream processing framework for high-throughput applications.

### [Bifrost Wiki](https://github.com/ledatelescope/bifrost/wiki)
### [Bifrost Roadmap](ROADMAP.md)

## Your first pipeline

```python
def generate_ten_arrays():
  for i in range(10):
    yield np.array([1, 0, 0])

def array_print(array):
  print array

blocks = [
  (NumpySourceBlock(generate_ten_arrays), {'out_1': 'raw'}),
  (NumpyBlock(np.fft.fft), {'in_1': 'raw', 'out_1':'fft'}),
  (NumpyBlock(array_print, outputs=0), {'in_1': 'fft'})]

Pipeline(blocks).main()
# [ 1.+0.j  1.+0.j  1.+0.j]
# [ 1.+0.j  1.+0.j  1.+0.j]
# ...
```

<!---
Should put an image of this pipeline here.
-->
## Feature overview

 * Designed for sustained high-throughput stream processing
 * Python and C++ APIs wrap fast C++/CUDA backend
 * Native support for both system (CPU) and CUDA (GPU) memory spaces and computation

 * Main modules
  - Ring buffer: Flexible and thread safe, supports CPU and GPU memory spaces
  - Transpose: Arbitrary transpose function for ND arrays

 * Experimental modules
  - UDP: Fast data capture with memory reordering and unpacking
  - Radio astronomy: High-performance signal processing operations

## Installation

### C library

Install dependencies:

    $ sudo apt-get install exuberant-ctags

### Python interface

Install dependencies:

 * [PyCLibrary fork](https://github.com/MatthieuDartiailh/pyclibrary)
 * Numpy
 * contextlib2
 * pint
 

```
$ sudo pip install numpy contextlib2 pint
```

### Bifrost installation

Edit **user.mk** to suit your system, then run:

    $ make -j
    $ sudo make install 

which will install the library and headers into /usr/local/lib and
/usr/local/include respectively.

You can call the following for a local Python installation:

    $ sudo make install PYINSTALLFLAGS="--prefix=$HOME/usr/local"

Note that the bifrost module's use of PyCLibrary means it must have
access to both the bifrost shared library and the bifrost headers at
import time. The LD_LIBRARY_PATH and BIFROST_INCLUDE_PATH environment
variables can be used to add search paths for these dependencies
respectively.

### Docker container

Install dependencies:

 * [Docker Engine](https://docs.docker.com/engine/installation/)
 * [NVIDIA Docker](https://github.com/NVIDIA/nvidia-docker)

Build Docker image:

    $ make docker

For CPU-only builds:

    $ make docker-cpu

Launch container:

    $ nvidia-docker run --rm -it ledatelescope/bifrost

## Documentation

Doxygen documentation can be generated by running:

    $ make doc

## Contributors

 * Ben Barsdell
 * Daniel Price
 * Miles Cranmer
 * Hugh Garsden
