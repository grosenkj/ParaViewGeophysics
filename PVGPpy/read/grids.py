__all__ = ['sgemsGrid', 'sgemsExtent', 'readPVGPGridExtents', 'readPVGPGrid']

import numpy as np
import csv
import os
from vtk.util import numpy_support as nps
import vtk
import json
import struct
import base64

def sgemsGrid(FileName, deli=' ', useTab=False, pdo=None):
    """
    Description
    -----------
    Generates vtkImageData from the uniform grid defined in the inout file in the SGeMS grid format. This format is simply the GSLIB format where the header line defines the dimensions of the uniform grid.

    Parameters
    ----------
    `FileName` : str
    - The file name / absolute path for the input file in SGeMS grid format.

    `deli` : str, optional
    - The input files delimiter. To use a tab delimiter please set the `useTab`.

    `useTab` : boolean, optional
    - A boolean that describes whether to use a tab delimiter.

    `pdo` : vtk.vtkImageData, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns vtkImageData

    """
    from PVGPpy.read import gslib
    if pdo is None:
        pdo = vtk.vtkImageData() # vtkImageData

    table, header = gslib(FileName, deli=deli, useTab=useTab, numIgLns=0, pdo=None)
    h = header.split(deli)
    n1,n2,n3 = int(h[0]), int(h[1]), int(h[2])

    pdo.SetDimensions(n1, n2, n3)
    pdo.SetExtent(0,n1-1, 0,n2-1, 0,n3-1)

    # now get arrays from table and add to point data of pdo
    for i in range(table.GetNumberOfColumns()):
        pdo.GetPointData().AddArray(table.GetColumn(i))
        #TODO: pdo.GetCellData().AddArray(VTK_data)
    del(table)
    return pdo

def sgemsExtent(FileName, deli=' ', useTab=False):
    """
    Description
    -----------
    Reads the input file for the SGeMS format to get output extents. Computationally inexpensive method to discover whole output extent.

    Parameters
    ----------
    `FileName` : str
    - The file name / absolute path for the input file in SGeMS grid format.

    `deli` : str, optional
    - The input files delimiter. To use a tab delimiter please set the `useTab`.

    `useTab` : boolean, optional
    - A boolean that describes whether to use a tab delimiter.

    Returns
    -------
    This returns a tuple of the whole extent for the uniform grid to be made of the input file (0,n1-1, 0,n2-1, 0,n3-1). This output should be directly passed to util.SetOutputWholeExtent() when used in programmable filters or source generation on the pipeline.

    """
    with open(FileName) as f:
        if (useTab):
            deli = '\t'
        reader = csv.reader(f, delimiter=deli)
        h = reader.next()
        n1,n2,n3 = int(h[0]), int(h[1]), int(h[2])
        f.close()
        return (0,n1-1, 0,n2-1, 0,n3-1)







#-----------
# PVGP Custom Grid file type
"""
This file reader will open a header file that points to a packed binary data files
The header will have Parameters for extent, spacing, origin, and number of arrays
Each data array will be in a seperate binary data file

Example Header in Json Format
"""


def _getdtypes(dtype):
    if dtype == 'float64':
        num_bytes = 8 # DOUBLE
        sdtype = 'd'
        vtktype = vtk.VTK_DOUBLE
    elif dtype == 'float32':
        num_bytes = 4 # FLOAT
        sdtype = 'f'
        vtktype = vtk.VTK_FLOAT
    elif 'int' in dtype:
        num_bytes = 4 # INTEGER
        sdtype = 'i'
        vtktype = vtk.VTK_INT
    else:
        raise Exception('dtype \'%s\' unknown.' % dtype)

    return dtype, sdtype, num_bytes, vtktype


def readPVGPGridExtents(headerfile):
    with open(headerfile, 'r') as f:
        lib = json.load(f)
    n1,n2,n3 = lib['extent']
    return (0,n1-1, 0,n2-1, 0,n3-1)


def readPVGPGrid(headerfile, pdo=None, path=None):
    """
    Description
    -----------
    Generates vtkImageData from the uniform grid defined in the PVGP uniformly gridded data format.

    Parameters
    ----------
    `headerfile` : str
    - The file name / absolute path for the input header file that cotains all parameters and pointers to file locations.

    `pdo` : vtk.vtkImageData, optional
    - A pointer to the output data object.

    `path` : str, optional
    - The absolute path to the PVGP grid database to override the path in the header file.

    Returns
    -------
    Returns vtkImageData

    """
    if pdo is None:
        pdo = vtk.vtkImageData() # vtkImageData
    # Read and parse header file
    with open(headerfile, 'r') as f:
        lib = json.load(f)
    basename = lib['basename']
    extent = lib['extent']
    spacing = lib['spacing']
    origin = lib['origin']
    order = lib['order']
    endian = lib['endian']
    numArrays = lib['numArrays']
    dataArrays = lib['dataArrays']
    if path is None:
        path = lib['originalPath']

    # Grab Parameters
    n1, n2, n3 = extent
    ox, oy, oz = origin
    sx, sy, sz = spacing
    # Setup vtkImageData
    pdo.SetDimensions(n1, n2, n3)
    pdo.SetExtent(0,n1-1, 0,n2-1, 0,n3-1)
    pdo.SetOrigin(ox, oy, oz)
    pdo.SetSpacing(sx, sy, sz)
    # Read in data arrays
    dataArrs = []
    dataNames = []
    vtktypes = []
    for darr in dataArrays:
        dataNames.append(darr)
        dtype, sdtype, num_bytes, vtktype = _getdtypes(dataArrays[darr]['dtype'])
        vtktypes.append(vtktype)
        # Grab and decode data array
        encoded = base64.b64decode(dataArrays[darr]['data'])

        raw = struct.unpack(endian+str(n1*n2*n3)+sdtype, encoded)
        dataArrs.append(np.asarray(raw, dtype=dtype))

    """TODO:
    if order is not 'F':
        # Reshape the arrays
        arr = np.reshape(arr, (n1,n2,n3), order=order).flatten(order='C')"""

    # vtk data arrays
    for i in range(numArrays):
        arr = dataArrs[i]
        VTK_data = nps.numpy_to_vtk(num_array=arr, deep=True, array_type=vtktypes[i])
        VTK_data.SetName(dataNames[i])
        pdo.GetPointData().AddArray(VTK_data)

    return pdo
