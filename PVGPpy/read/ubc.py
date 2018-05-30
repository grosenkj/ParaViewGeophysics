__all__ = [
    # 2D Mesh
    'ubcMesh2D',
    'ubcModel2D',

    # 3D Mesh
    'ubcMesh3D',
    'ubcModel3D',

    # General Stuff
    'ubcExtent',
    'placeModelOnMesh',
    'readUBCMesh',

    # OcTree
    'ubcOcTree',
    'placeModelOnOcTreeMesh']

import numpy as np
import struct
import csv
import os
from vtk.util import numpy_support as nps
import vtk
# Import Helpers:
from ._helpers import *


#------------------------------------------------------------------#
#----------------------     UBC MESH 2D    ------------------------#
#------------------------------------------------------------------#

def _ubcMesh2D_part(FileName):
    # This is a helper method to read file contents of mesh
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')

    def _genTup(sft, n):
        # This reads in the data for a dimension
        pts = []
        disc = []
        for i in range(n):
            ln = fileLines[i+sft].split('!')[0].split()
            if i is 0:
                o = ln[0]
                pts.append(o)
                ln = [ln[1],ln[2]]
            pts.append(ln[0])
            disc.append(ln[1])
        return pts, disc

    # Get the number of lines for each dimension
    nx = int(fileLines[0].split('!')[0])
    nz = int(fileLines[nx+1].split('!')[0])

    # Get the origins and tups for both dimensions
    xpts, xdisc = _genTup(1, nx)
    zpts, zdisc = _genTup(2+nx, nz)

    return xpts, xdisc, zpts, zdisc

def ubcMesh2D(FileName, pdo=None):
    """
    Description
    -----------
    This method reads a UBC 2D Mesh file and builds an empty vtkRectilinearGrid for data to be inserted into. [Format Specs](http://giftoolscookbook.readthedocs.io/en/latest/content/fileFormats/mesh2Dfile.html)

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 3D Mesh Format.

    `pdo` : vtk.vtkRectilinearGrid, optional
    - The output data object

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 3D Mesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkRectilinearGrid() # vtkRectilinearGrid

    # Read in data from file
    xpts, xdisc, zpts, zdisc = _ubcMesh2D_part(FileName)

    nx = np.sum(np.array(xdisc,dtype=int))+1
    nz = np.sum(np.array(zdisc,dtype=int))+1

    # Now generate the vtkRectilinear Grid
    def _genCoords(pts, disc):
        c = [float(pts[0])]
        for i in range(len(pts)-1):
            start = float(pts[i])
            stop = float(pts[i+1])
            num = int(disc[i])
            w = (stop-start)/num

            for j in range(1,num):
                c.append(start + (j)*w)
            c.append(stop)
        c = np.array(c,dtype=float)
        return nps.numpy_to_vtk(num_array=c,deep=True)

    xcoords = _genCoords(xpts, xdisc)
    zcoords = _genCoords(zpts, zdisc)
    ycoords = nps.numpy_to_vtk(num_array=np.zeros(1),deep=True)

    pdo.SetDimensions(nx,2,nz) # note this subtracts 1
    pdo.SetXCoordinates(xcoords)
    pdo.SetYCoordinates(ycoords)
    pdo.SetZCoordinates(zcoords)

    return pdo

def ubcModel2D(FileName):
    """
    Description
    -----------
    Reads a 2D model file and returns a 1D NumPy float array. Use the placeModelOnMesh() method to associate with a grid.

    Parameters
    ----------
    `FileName` : str
    - The model filename as an absolute path for the input model file in UBCMesh Model Format.

    Returns
    -------
    Returns a NumPy float array that holds the model data read from the file. Use the placeModelOnMesh() method to associate with a grid.
    """
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')
    dim = np.array(fileLines[0].split(), dtype=int)
    data = np.genfromtxt((line.encode('utf8') for line in fileLines[1::]), dtype=np.float)
    if np.shape(data)[0] != dim[1] and np.shape(data)[1] != dim[0]:
        raise Exception('Mode file `%s` improperly formatted.' % FileName)
    return data.flatten(order='F')

def _ubcMeshData2D(FileName_Mesh, FileName_Model, dataNm='', pdo=None):
    """Helper method to read a 2D mesh"""
    # If no name given for data by user, use the basename of the file
    if dataNm == '':
        dataNm = os.path.basename(FileName_Model)
    # Construct/read the mesh
    mesh = ubcMesh2D(FileName_Mesh, pdo=pdo)
    # Read the model data
    model = ubcModel2D(FileName_Model)
    # Place the model data onto the mesh
    grd = placeModelOnMesh(mesh, model, dataNm)
    return grd


#------------------------------------------------------------------#
#----------------------     UBC MESH 3D    ------------------------#
#------------------------------------------------------------------#

def ubcMesh3D(FileName, pdo=None):
    """
    Description
    -----------
    This method reads a UBC 3D Mesh file and builds an empty vtkRectilinearGrid for data to be inserted into.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 3D Mesh Format.

    `pdo` : vtk.vtkRectilinearGrid, optional
    - The output data object

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 3D Mesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkRectilinearGrid() # vtkRectilinearGrid

    # Define a function to parse cell size lines
    def parse_cell_size_line(line_str):
        '''
        Function that parses a UBC cell size line

        returns: Numpy array of the cell sizes

        '''
        line_list = []
        for seg in line_str.split():
            if '*' in seg:
                sp = seg.split('*')
                seg_arr = np.ones((int(sp[0]),)) * float(sp[1])
            else:
                seg_arr = np.array([float(seg)], float)
            line_list.append(seg_arr)
        return np.concatenate(line_list)

    #--- Read in the mesh ---#
    fileLines = np.genfromtxt(FileName, dtype=str,
        delimiter='\n', comments='!')

    # Get mesh dimensions
    dim = np.array(fileLines[0].
        split('!')[0].split(), dtype=int)
    dim = (dim[0]+1, dim[1]+1, dim[2]+1)

    # The origin corner (Southwest-top)
    #- Remember UBC format specifies down as the positive Z
    #- Easting, Northing, Altitude
    oo = np.array(
        fileLines[1].split('!')[0].split(),
        dtype=float
    )

    vv = [None, None, None]
    # Now extract cell sizes
    # Iterating of the lines containing the cell size info
    for i, cell_line in enumerate(fileLines[2:5]):
        # Remove the comments (if any) for the end of the line
        spac_str = cell_line.split('!')[0]
        # Now check if there are any of the repeating spacings
        # Parse the spac_str
        spac = parse_cell_size_line(spac_str)

        # Now check that we have correct number widths for given dimension
        if len(spac) != dim[i] - 1:
            raise Exception('More spacings specifed than extent defined allows for dimension %d' % i)
        # Now generate the coordinates for this dimension
        if (i == 2):
            # Z dimension (down is positive Z!)
            #  TODO: what is the correct way to do this?
            s = oo[i] - np.cumsum(np.r_[0, spac])
        else:
            # X and Y dimensions
            s = oo[i] + np.cumsum(np.r_[0, spac])
        # Convert to VTK array for setting coordinates
        vv[i] = nps.numpy_to_vtk(num_array=s, deep=True)

    # Set the dims and coordinates for the output
    pdo.SetDimensions(dim[0], dim[1], dim[2])
    pdo.SetXCoordinates(vv[0])
    pdo.SetYCoordinates(vv[1])
    pdo.SetZCoordinates(vv[2])

    return pdo

def ubcModel3D(FileName):
    """
    Description
    -----------
    Reads the 3D model file and returns a 1D NumPy float array. Use the placeModelOnMesh() method to associate with a grid.

    Parameters
    ----------
    `FileName` : str
    - The model filename as an absolute path for the input model file in UBC 3D Model Model Format.

    Returns
    -------
    Returns a NumPy float array that holds the model data read from the file. Use the placeModelOnMesh() method to associate with a grid.
    """
    fileLines = np.genfromtxt(FileName, dtype=str, delimiter='\n', comments='!')
    data = np.genfromtxt((line.encode('utf8') for line in fileLines), dtype=np.float)
    return data

def _ubcMeshData3D(FileName_Mesh, FileName_Model, dataNm='', pdo=None):
    """Helper method to read a 3D mesh"""
    # If no name given for data by user, use the basename of the file
    if dataNm == '':
        dataNm = os.path.basename(FileName_Model)
    # Construct/read the mesh
    mesh = ubcMesh3D(FileName_Mesh, pdo=pdo)
    # Read the model data
    model = ubcModel3D(FileName_Model)
    # Place the model data onto the mesh
    grd = placeModelOnMesh(mesh, model, dataNm)
    return grd

#------------------------------------------------------------------#
# General Methods for UBC Formats
#------------------------------------------------------------------#

def ubcExtent(FileName):
    """
    Description
    -----------
    Reads the mesh file for the UBC 2D/3D Mesh or OcTree format to get output extents. Computationally inexpensive method to discover whole output extent.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in a UBC Format with extents defined on the first line.

    Returns
    -------
    This returns a tuple of the whole extent for the grid to be made of the input mesh file (0,n1-1, 0,n2-1, 0,n3-1). This output should be directly passed to util.SetOutputWholeExtent() when used in programmable filters or source generation on the pipeline.

    """
    # Read the mesh file as line strings, remove lines with comment = !
    v = np.array(np.__version__.split('.'), dtype=int)
    if v[0] >= 1 and v[1] >= 10:
        # max_rows in numpy versions >= 1.10
        msh = np.genfromtxt(FileName, delimiter='\n', dtype=np.str,comments='!', max_rows=1)
    else:
        # This reads whole file :(
        msh = np.genfromtxt(FileName, delimiter='\n', dtype=np.str, comments='!')[0]
    # Fist line is the size of the model
    sizeM = np.array(msh.ravel()[0].split(), dtype=int)
    # Check if the mesh is a UBC 2D mesh
    if sizeM.shape[0] == 1:
        # Read in data from file
        xpts, xdisc, zpts, zdisc = _ubcMesh2D_part(FileName)
        nx = np.sum(np.array(xdisc,dtype=int))+1
        nz = np.sum(np.array(zdisc,dtype=int))+1
        return (0,nx, 0,1,  0,nz)
    # Check if the mesh is a UBC 3D mesh or OcTree
    elif sizeM.shape[0] >= 3:
        # Get mesh dimensions
        dim = sizeM[0:3]
        ne,nn,nz = dim[0], dim[1], dim[2]
        return (0,ne, 0,nn, 0,nz)
    else:
        raise Exception('File format not recognized')


def placeModelOnMesh(mesh, model, dataNm='Data'):
    """
    Description
    -----------
    Places model data onto a mesh. This is for the UBC Grid data reaers to associate model data with the mesh grid.

    Parameters
    ----------
    `mesh` : vtkRectilinearGrid
    - The vtkRectilinearGrid that is the mesh to place the model data upon.

    `model` : NumPy float array
    - A NumPy float array that holds all of the data to place inside of the mesh's cells.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    Returns
    -------
    Returns the input vtkRectilinearGrid with model data appended.

    """
    # model.GetNumberOfValues() if model is vtkDataArray
    # Make sure this model file fits the dimensions of the mesh
    ext = mesh.GetExtent()
    n1,n2,n3 = ext[1],ext[3],ext[5]
    if (n1*n2*n3 < len(model)):
        raise Exception('This model file has more data than the given mesh has cells to hold.')
    elif (n1*n2*n3 > len(model)):
        raise Exception('This model file does not have enough data to fill the given mesh\'s cells.')

    # Swap axes because VTK structures the coordinates a bit differently
    #-  This is absolutely crucial!
    #-  Do not play with unless you know what you are doing!
    model = np.reshape(model, (n1,n2,n3))
    model = np.swapaxes(model,0,1)
    model = np.swapaxes(model,0,2)
    model = model.flatten()

    # Convert data to VTK data structure and append to output
    c = nps.numpy_to_vtk(num_array=model,deep=True)
    c.SetName(dataNm)
    # THIS IS CELL DATA! Add the model data to CELL data:
    mesh.GetCellData().AddArray(c)
    return mesh


def readUBCMesh(FileName_Mesh, FileName_Model, dataNm='', pdo=None):
    """
    Description
    -----------
    Wrapper to Read UBC GIF 2D and 3D meshes. UBC Mesh 2D/3D models are defined using a 2-file format. The "mesh" file describes how the data is descritized. The "model" file lists the physical property values for all cells in a mesh. A model file is meaningless without an associated mesh file. If the mesh file is 2D, then then model file must also be in the 2D format (same for 3D).

    Parameters
    ----------
    `FileName_Mesh` : str
    - The mesh filename as an absolute path for the input mesh file in UBC 2D/3D Mesh Format

    `FileName_Model` : str
    - The model filename as an absolute path for the input model file in UBC 2D/3D Model Format.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    `pdo` : vtk.vtkRectilinearGrid, optional
    - The output data object

    Returns
    -------
    Returns a vtkRectilinearGrid generated from the UBC 2D/3D Mesh grid. Mesh is defined by the input mesh file. Cell data is defined by the input model file.
    """
    # Read the mesh file as line strings, remove lines with comment = !
    v = np.array(np.__version__.split('.'), dtype=int)
    if v[0] >= 1 and v[1] >= 10:
        # max_rows in numpy versions >= 1.10
        msh = np.genfromtxt(FileName_Mesh, delimiter='\n', dtype=np.str,comments='!', max_rows=1)
    else:
        # This reads whole file :(
        msh = np.genfromtxt(FileName_Mesh, delimiter='\n', dtype=np.str, comments='!')[0]
    # Fist line is the size of the model
    sizeM = np.array(msh.ravel()[0].split(), dtype=float)
    # Check if the mesh is a UBC 2D mesh
    if sizeM.shape[0] == 1:
        _ubcMeshData2D(FileName_Mesh, FileName_Model, dataNm=dataNm, pdo=pdo)
    # Check if the mesh is a UBC 3D mesh
    elif sizeM.shape[0] == 3:
        _ubcMeshData3D(FileName_Mesh, FileName_Model, dataNm=dataNm, pdo=pdo)
    else:
        raise Exception('File format not recognized')
    return pdo




#------------------------------------------------------------------#
#-----------------------    UBC OcTree    -------------------------#
#------------------------------------------------------------------#

def ubcOcTree(FileName, dataNm='', pdo=None):
    """
    Description
    -----------
    This method reads a UBC OcTree Mesh file and builds a vtkUnstructuredGrid of the data in the file. This method generates the vtkUnstructuredGrid without any data attributes.

    Parameters
    ----------
    `FileName` : str
    - The mesh filename as an absolute path for the input mesh file in UBC OcTree format.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkRectilinearGrid.

    `pdo` : vtk.vtkUnstructuredGrid, optional
    - A pointer to the output data object.

    Returns
    -------
    Returns a vtkUnstructuredGrid generated from the UBCMesh grid. Mesh is defined by the input mesh file. No data attributes here, simply an empty mesh. Use the placeModelOnMesh() method to associate with model data.

    """
    if pdo is None:
        pdo = vtk.vtkUnstructuredGrid() # vtkUnstructuredGrid

    #--- Read in the mesh ---#
    fileLines = np.genfromtxt(FileName, dtype=str,
        delimiter='\n', comments='!')

    # Get mesh dimensions
    dim = np.array(fileLines[0].
        split('!')[0].split(), dtype=int)
    # First three values are the number of cells in the core mesh and remaining 6 values are padding for the core region.
    pad = dim[3:6] # TODO: check if there because optional... might throw error if not there
    dim = dim[0:3]
    ne,nn,nz = dim[0], dim[1], dim[2]
    # This is not true
    # if np.unique(dim).size > 1:
    #     raise Exception('OcTree meshes must have the same number of cells in all directions.')

    # The origin corner (Southwest-top)
    #- Remember UBC format specifies down as the positive Z
    #- Easting, Northing, Altitude
    oo = np.array(
        fileLines[1].split('!')[0].split(),
        dtype=float
    )
    oe,on,oz = oo[0],oo[1],oo[2]

    # Widths of the core cells in the Easting, Northing, and Vertical directions.
    ww = np.array(
        fileLines[2].split('!')[0].split(),
        dtype=float
    )
    we,wn,wz = ww[0],ww[1],ww[2]

    # Number of cells in OcTree mesh
    numCells = np.array(
        fileLines[3].split('!')[0].split(),
        dtype=float
    )

    # Read the remainder of the file containing the index arrays
    indArr = np.genfromtxt(
        (line.encode('utf8') for line in fileLines[4::]), dtype=np.int)

    # Start processing the information
    # Make vectors of the base mesh node, starting in the wsb corner
    vec_full_nx = np.cumsum(np.hstack((oe, we * np.ones(ne))))
    vec_full_ny = np.cumsum(np.hstack((on, wn * np.ones(nn))))
    vec_full_nz = np.cumsum(np.hstack((oz - wz * nz, wz * np.ones(nz))))
    # Make indices
    indC = indArr[:, 0:3] + np.array([-1, -1, -1])  # Shift to be 0 indexed
    # Flip the z-ind to start from bottom
    indC[:, 2] = nz - indC[:, 2] - indArr[:, 3]
    cell_size = np.reshape(indArr[:, 3], (len(indArr[:, 3]), 1))
    cell_zero = np.zeros((len(cell_size), 1), dtype=np.int)
    # Need to reference the nodal numbers to form the cell.
    # Find the 8 corners of each cell
    #
    #             z+   y+
    #             |  /
    #             | /
    #             |/_ _ _ x+
    #
    #    N7--------N8
    #   /|         /|
    #  N5--------N6 |
    #  | |        | |
    #  | N3-------|N4
    #  |/         |/
    #  N1--------N2

    # UBC Octree indexes always the top-left-close corner first
    # For to define the cells in UBC order
    cell_n1 = indC + np.hstack((cell_zero, cell_zero, cell_zero))  # Node 1 in all cells
    cell_n2 = indC + np.hstack((cell_size, cell_zero, cell_zero))  # Node 2 in all cells
    cell_n3 = indC + np.hstack((cell_zero, cell_size, cell_zero))  # Node 3 in all cells
    cell_n4 = indC + np.hstack((cell_size, cell_size, cell_zero))  # Node 4 in all cells
    cell_n5 = indC + np.hstack((cell_zero, cell_zero, cell_size))  # Node 5 in all cells
    cell_n6 = indC + np.hstack((cell_size, cell_zero, cell_size))  # Node 6 in all cells
    cell_n7 = indC + np.hstack((cell_zero, cell_size, cell_size))  # Node 7 in all cells
    cell_n8 = indC + np.hstack((cell_size, cell_size, cell_size))  # Node 8 in all cells
    # Sort the nodal index to be from the south-west-bottom most corner,
    # comply with SimPEG ordering
    # NOTE: Is not needed but prefered
    ind_cell_corner = np.argsort(
        cell_n1.view(','.join(3 * ['int'])), axis=0, order=('f2', 'f1', 'f0'))
    sortcell_n1 = cell_n1[ind_cell_corner][:, 0, :]
    sortcell_n2 = cell_n2[ind_cell_corner][:, 0, :]
    sortcell_n3 = cell_n3[ind_cell_corner][:, 0, :]
    sortcell_n4 = cell_n4[ind_cell_corner][:, 0, :]
    sortcell_n5 = cell_n5[ind_cell_corner][:, 0, :]
    sortcell_n6 = cell_n6[ind_cell_corner][:, 0, :]
    sortcell_n7 = cell_n7[ind_cell_corner][:, 0, :]
    sortcell_n8 = cell_n8[ind_cell_corner][:, 0, :]
    # Find the unique nodes
    all_nodes = np.concatenate((
        sortcell_n1,
        sortcell_n2,
        sortcell_n3,
        sortcell_n4,
        sortcell_n5,
        sortcell_n6,
        sortcell_n7,
        sortcell_n8), axis=0)
    # Make a rec array to search for uniques
    all_nodes_rec = all_nodes.view(','.join(3 * ['int']))[:, 0]
    unique_nodes, ind_nodes_vec = np.unique(all_nodes_rec, return_inverse=True)

    # Reshape the matrix
    ind_nodes_mat = ind_nodes_vec.reshape(((8, ind_nodes_vec.size / 8))).T
    ind_nodes_full = np.concatenate((
        np.ones((
            ind_nodes_mat.shape[0],
            1), dtype=np.int64) * ind_nodes_mat.shape[1],
        ind_nodes_mat), axis=1).ravel()

    # Make the VTK object
    # Make the points.
    ptsArr = np.concatenate((
        vec_full_nx[unique_nodes['f0']].reshape(-1, 1),
        vec_full_ny[unique_nodes['f1']].reshape(-1, 1),
        vec_full_nz[unique_nodes['f2']].reshape(-1, 1)), axis=1)
    vtkPtsData = nps.numpy_to_vtk(ptsArr, deep=1)
    vtkPts = vtk.vtkPoints()
    vtkPts.SetData(vtkPtsData)

    # Make the cells
    # Cells -cell array
    CellArr = vtk.vtkCellArray()
    CellArr.SetNumberOfCells(numCells)
    CellArr.SetCells(
        numCells,
        nps.numpy_to_vtkIdTypeArray(
            np.ascontiguousarray(ind_nodes_full), deep=1))

    # Make the object
    pdo = vtk.vtkUnstructuredGrid()
    # Set the objects properties
    pdo.SetPoints(vtkPts)
    pdo.SetCells(vtk.VTK_VOXEL, CellArr)

    # Add the indexing of the cell's
    vtkIndexArr = nps.numpy_to_vtk(
        np.ascontiguousarray(ind_cell_corner.ravel()), deep=1)
    vtkIndexArr.SetName('index_cell_corner')
    pdo.GetCellData().AddArray(vtkIndexArr)

    ################
    print('This reader is not fully implemented yet')
    # print(indArr)
    ################

    return pdo


def placeModelOnOcTreeMesh(mesh, model, dataNm='Data'):
    """
    Description
    -----------
    Places model data onto a mesh. This is for the UBC Grid data reaers to associate model data with the mesh grid.

    Parameters
    ----------
    `mesh` : vtkUnstructuredGrid
    - The vtkUnstructuredGrid that is the mesh to place the model data upon.
        Needs to have been read in by ubcOcTree

    `model` : NumPy float array
    - A NumPy float array that holds all of the data to place inside of the mesh's cells.

    `dataNm` : str, optional
    - The name of the model data array once placed on the vtkUnstructuredGrid.

    Returns
    -------
    Returns the input vtkUnstructuredGrid with model data appended.

    """
    # model.GetNumberOfValues() if model is vtkDataArray
    # Make sure this model file fits the dimensions of the mesh
    numCells = mesh.GetNumberOfCells()
    if (numCells < len(model)):
        raise Exception('This model file has more data than the given mesh has cells to hold.')
    elif (numCells > len(model)):
        raise Exception('This model file does not have enough data to fill the given mesh\'s cells.')

    # Swap axes because VTK structures the coordinates a bit differently
    #-  This is absolutely crucial!
    #-  Do not play with unless you know what you are doing!
    ind_reorder = nps.vtk_to_numpy(
        mesh.GetCellData().GetArray('index_cell_corner'))

    model = model[ind_reorder]

    # Convert data to VTK data structure and append to output
    c = nps.numpy_to_vtk(num_array=model, deep=True)
    c.SetName(dataNm)
    # THIS IS CELL DATA! Add the model data to CELL data:
    mesh.GetCellData().AddArray(c)
    return mesh
