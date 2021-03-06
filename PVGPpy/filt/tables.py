__all__ = [
    'reshapeTable',
    'latLonTableToCartesian'
]

import vtk
import numpy as np
from vtk.util import numpy_support as nps
from vtk.numpy_interface import dataset_adapter as dsa
from PVGPpy.helpers import *

#---- Reshape Table ----#

def reshapeTable(pdi, nrows, ncols, names=None, order='C', pdo=None):
    """
    Todo Description
    """
    if pdo is None:
        pdo = vtk.vtkTable()
    # Get number of columns
    cols = pdi.GetNumberOfColumns()
    # Get number of rows
    rows = pdi.GetColumn(0).GetNumberOfTuples() # TODO is the necessary?

    if names is not None and len(names) is not 0:
        # parse the names (a semicolon seperated list of names)
        names = names.split(';')
        num = len(names)
        if num < ncols:
            for i in range(num, ncols):
                names.append('Field %d' % i)
        elif num > ncols:
            raise Exception('Too many array names. `ncols` specified as %d and %d names given.' % (ncols, num))
    else:
        names = ['Field %d' % i for i in range(ncols)]

    # Make a 2D numpy array and fill with data from input table
    data = np.empty((cols,rows))
    for i in range(cols):
        c = pdi.GetColumn(i)
        data[i] = nps.vtk_to_numpy(c)

    if ((ncols*nrows) != (cols*rows)):
        raise Exception('Total number of elements must remain %d. Check reshape dimensions.' % (cols*rows))

    # Use numpy.reshape() to reshape data NOTE: only 2D because its a table
    # NOTE: column access of this reshape is not contigous
    data = np.array(np.reshape(data, (nrows,ncols), order=order))
    pdo.SetNumberOfRows(nrows)

    # Add new array to output table and assign incremental names (e.g. Field0)
    for i in range(ncols):
        # Make a contigous array from the column we want
        col = np.array(data[:,i])
        # allow type to be determined by input
        insert = nps.numpy_to_vtk(num_array=col, deep=True) # array_type=vtk.VTK_FLOAT
        # VTK arrays need a name. Set arbitrarily
        insert.SetName(names[i])
        #pdo.AddColumn(insert) # these are not getting added to the output table
        # ... work around:
        pdo.GetRowData().AddArray(insert) # NOTE: this is in the FieldData

    return pdo


#---- LatLon to Cartesian ----#
def latLonTableToCartesian(pdi, arrlat, arrlon, arralt, radius=6371.0, pdo=None):
    # TODO: This is very poorly done
    # TODO: filter works but assumes a spherical earth wich is VERY wrong
    # NOTE: Mismatches the vtkEarth Source however so we gonna keep it this way
    raise Exception('latLonTableToCartesian() not currently implemented.')
    if pdo is None:
        pdo = vtk.vtkPolyData()
    #pdo.DeepCopy(pdi)
    wpdo = dsa.WrapDataObject(pdo)
    import sys
    sys.path.append('/Users/bane/miniconda3/lib/python3.6/site-packages/')
    import utm

    # Get the input arrays
    (namelat, fieldlat) = arrlat[0], arrlat[1]
    (namelon, fieldlon) = arrlon[0], arrlon[1]
    (namealt, fieldalt) = arralt[0], arralt[1]
    wpdi = dsa.WrapDataObject(pdi)
    lat = getArray(wpdi, fieldlat, namelat)
    lon = getArray(wpdi, fieldlon, namelon)
    alt = getArray(wpdi, fieldalt, namealt)
    if len(lat) != len(lon) or len(lat) != len(alt):
        raise Exception('Latitude, Longitude, and Altitude arrays must be same length.')

    coords = np.empty((len(lat),3))

    for i in range(len(lat)):
        (e, n, zN, zL) = utm.from_latlon(lat[i], lon[i])
        coords[i,0] = e
        coords[i,1] = n
    coords[:,2] = alt

    #insert = nps.numpy_to_vtk(num_array=coords, deep=True)
    #insert.SetName('Coordinates')
    # Add coords to ouptut table
    wpdo.Points = coords
    pts = vtk.vtkPoints()
    polys = vtk.vtkCellArray()
    k = 1
    # TODO: wee need point cells????
    for r in coords:
        pts.InsertNextPoint(r[0],r[1],r[2])
        polys.InsertNextCell(1)
        polys.InsertCellPoint(k)
        k = k + 1
    #polys.Allocate()
    pdo.SetPoints(pts)
    pdo.SetPolys(polys)
    # Add other arrays to output appropriately
    pdo = copyArraysToPointData(pdi, pdo, fieldlat)

    return pdo
