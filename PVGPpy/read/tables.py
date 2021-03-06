__all__ = ['gslib', 'packedBinaries', 'madagascar', 'delimitedText']

import numpy as np
import struct
import csv
import os
from vtk.util import numpy_support as nps
import vtk
import ast
import warnings
# Import Helpers:
from ._helpers import *


def gslib(FileName, deli=' ', useTab=False, numIgLns=0, pdo=None):
    """
    Description
    -----------
    Reads a GSLIB file format to a vtkTable. The GSLIB file format has headers lines followed by the data as a space delimited ASCI file (this filter is set up to allow you to choose any single character delimiter). The first header line is the title and will be printed to the console. This line may have the dimensions for a grid to be made of the data. The second line is the number (n) of columns of data. The next n lines are the variable names for the data in each column. You are allowed up to ten characters for the variable name. The data follow with a space between each field (column).

    Parameters
    ----------
    `FileName` : str
    - The absolute file name with path to read.

    `deli` : str
    - The input files delimiter. To use a tab delimiter please set the `useTab`.

    `useTab` : boolean
    - A boolean that describes whether to use a tab delimiter.

    `numIgLns` : int
    - The integer number of lines to ignore.

    `pdo` : vtk.vtkTable, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkTable of the input data file.

    """
    if pdo is None:
        pdo = vtk.vtkTable() # vtkTable

    if (useTab):
        deli = '\t'

    titles = []
    data = []
    with open(FileName) as f:
        reader = csv.reader(f, delimiter=deli)
        # Skip defined lines
        for i in range(numIgLns):
            next(f)

        # Get file header (part of format)
        header = next(f) # TODO: do something with the header
        #print(os.path.basename(FileName) + ': ' + header)
        # Get titles
        numCols = int(next(f))
        for i in range(numCols):
            titles.append(next(f).rstrip('\r\n'))

        # Read data
        for row in reader:
            data.append(row)

    _rows2table(data, titles, pdo)

    return pdo, header



def packedBinaries(FileName, dataNm=None, endian='>', dtype='f', pdo=None):
    """
    Description
    -----------
    This reads in float or double data that is packed into a binary file format. It will treat the data as one long array and make a vtkTable with one column of that data. The reader uses defaults to import as floats with native endianness. Use the Table to Uniform Grid or the Reshape Table filters to give more meaning to the data. We chose to use a vtkTable object as the output of this reader because it gives us more flexibility in the filters we can apply to this data down the pipeline and keeps thing simple when using filters in this repository.

    Parameters
    ----------
    `FileName` : str
    - The absolute file name with path to read.

    `dataNm` : str, optional
    - A string name to use for the constructed vtkDataArray.

    `endian` : char, optional
    - The endianness to unpack the values in struct.unpack(). Defaults to Big Endian `>`.

    `dtype` : char, optional
    - A char to chose the data type when unpacking with struct.unpack(). Defaults to float `f`.

    `pdo` : vtk.vtkTable, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkTable of the input data file with a single column being the data read.

    """
    if pdo is None:
        pdo = vtk.vtkTable() # vtkTable


    if dtype is 'd':
        num_bytes = 8 # DOUBLE
        vtktype = vtk.VTK_DOUBLE
    elif dtype is 'f':
        num_bytes = 4 # FLOAT
        vtktype = vtk.VTK_FLOAT
    elif dtype is 'i':
        num_bytes = 4 # INTEGER
        vtktype = vtk.VTK_INT
    else:
        raise Exception('dtype \'%s\' unknown/.' % dtype)

    tn = os.stat(FileName).st_size / num_bytes
    tn_string = str(tn)
    raw = []
    with open(FileName, 'rb') as file:
        # Unpack by num_bytes
        raw = struct.unpack(endian+tn_string+dtype, file.read(num_bytes*tn))

    # Put raw data into vtk array
    # TODO: dynamic typing
    data = nps.numpy_to_vtk(num_array=raw, deep=True, array_type=vtktype)

    if dataNm is None or dataNm == '' or dataNm == 'values':
        dataNm = os.path.splitext(os.path.basename(FileName))[0]
    data.SetName(dataNm)

    # Table with single column of data only
    pdo.AddColumn(data)

    return pdo

def madagascar(FileName, dataNm=None, endian='>', dtype='f', pdo=None):
    """
    Description
    -----------
    This reads in float or double data that is packed into a Madagascar binary file format with a leader header. The reader ignores all of the ascii header details by searching for the sequence of three special characters: EOL EOL EOT (\014\014\004) and it will treat the followng binary packed data as one long array and make a vtkTable with one column of that data. The reader uses defaults to import as floats with native endianness. Use the Table to Uniform Grid or the Reshape Table filters to give more meaning to the data. We will later implement the ability to create a gridded volume from the header info. This reader is a quick fix for Samir. We chose to use a vtkTable object as the output of this reader because it gives us more flexibility in the filters we can apply to this data down the pipeline and keeps thing simple when using filters in this repository.
    Details: http://www.ahay.org/wiki/RSF_Comprehensive_Description#Single-stream_RSF

    Parameters
    ----------
    `FileName` : str
    - The absolute file name with path to read.

    `dataNm` : str, optional
    - A string name to use for the constructed vtkDataArray.

    `endian` : char, optional
    - The endianness to unpack the values in struct.unpack(). Defaults to Big Endian `>`.

    `dtype` : char, optional
    - A char to chose the data type when unpacking with struct.unpack(). Defaults to float `f`.

    `pdo` : vtk.vtkTable, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkTable of the input data file with a single column being the data read.

    """
    if pdo is None:
        pdo = vtk.vtkTable() # vtkTable


    if dtype is 'd':
        num_bytes = 8 # DOUBLE
        vtktype = vtk.VTK_DOUBLE
    elif dtype is 'f':
        num_bytes = 4 # FLOAT
        vtktype = vtk.VTK_FLOAT
    elif dtype is 'i':
        num_bytes = 4 # INTEGER
        vtktype = vtk.VTK_INT
    else:
        raise Exception('dtype \'%s\' unknown/.' % dtype)

    raw = []
    with open(FileName, 'r') as file:
        ctlseq = b'\014\014\004'
        rpl = b''
        raw = file.read()
        idx = raw.find(ctlseq)
        if idx == -1:
            warnings.warn('This is not a single stream RSF format file. Treating entire file as packed binary data.')
        else:
            raw = raw[idx:] # deletes the header
            raw = raw.replace(ctlseq, rpl) # removes the control sequence
        tn = len(raw)/num_bytes
        fmt = endian+str(int(tn))+dtype
        raw = struct.unpack(fmt, raw)

    # Put raw data into vtk array
    # TODO: dynamic typing
    data = nps.numpy_to_vtk(num_array=raw, deep=True, array_type=vtktype)
    if dataNm is None or dataNm == '' or dataNm == 'values':
        dataNm = os.path.splitext(os.path.basename(FileName))[0]
    data.SetName(dataNm)

    # Table with single column of data only
    pdo.AddColumn(data)

    return pdo


def delimitedText(FileName, deli=' ', useTab=False, hasTits=True, numIgLns=0, pdo=None):
    """
    Description
    -----------
    This reader will take in any delimited text file and make a vtkTable from it. This is not much different than the default .txt or .csv reader in ParaView, however it gives us room to use our own extensions and a little more flexibility in the structure of the files we import.


    Parameters
    ----------
    `FileName` : str
    - The absolute file name with path to read.

    `deli` : str
    - The input files delimiter. To use a tab delimiter please set the `useTab`.

    `useTab` : boolean, optional
    - A boolean that describes whether to use a tab delimiter

    `hasTits` : boolean, optional
    - A boolean for if the delimited file has header titles for the data arrays.

    `numIgLns` : int
    - The integer number of lines to ignore

    `pdo` : vtk.vtkTable, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkTable of the input data file.

    """
    if pdo is None:
        pdo = vtk.vtkTable() # vtkTable

    if (useTab):
        deli = '\t'

    titles = []
    data = []
    with open(FileName) as f:
        reader = csv.reader(f, delimiter=deli)
        # Skip header lines
        for i in range(numIgLns):
            reader.next()
        # Get titles
        if (hasTits):
            titles = reader.next()
        else:
            # Bulild arbitrary titles for length of first row
            row = reader.next()
            data.append(row)
            for i in range(len(row)):
                titles.append('Field %d' % i)
        # Read data
        for row in reader:
            # Parse values here
            data.append(row)

    _rows2table(data, titles, pdo)

    return pdo
