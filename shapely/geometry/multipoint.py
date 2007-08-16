"""
Multiple points.
"""

from ctypes import byref, c_double, c_int, c_void_p, cast, POINTER, pointer

from shapely.geos import lgeos
from shapely.geometry.base import BaseGeometry, GeometrySequence
from shapely.geometry.point import Point, geos_point_from_py


def geos_multipoint_from_py(ob):
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        n = array['shape'][1]
        assert m >= 1
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        cp = cast(array['data'][0], POINTER(c_double))

        # Array of pointers to sub-geometries
        subs = (c_void_p * m)()

        for i in xrange(m):
            geom, ndims = geos_point_from_py(cp[n*i:n*i+2])
            subs[i] = cast(geom, c_void_p)

    except AttributeError:
        # Fall back on list
        m = len(ob)
        n = len(ob[0])
        assert n == 2 or n == 3

        # Array of pointers to point geometries
        subs = (c_void_p * m)()
        
        # add to coordinate sequence
        for i in xrange(m):
            coords = ob[i]
            geom, ndims = geos_point_from_py(coords)
            subs[i] = cast(geom, c_void_p)
            
    return (lgeos.GEOSGeom_createCollection(4, subs, m), n)


class MultiPoint(BaseGeometry):

    """A multiple point geometry.
    """

    def __init__(self, coordinates=None):
        """Initialize.

        Parameters
        ----------
        
        coordinates : sequence or array
            This may be an object that satisfies the numpy array protocol,
            providing an M x 2 or M x 3 (with z) array, or it may be a sequence
            of x, y (,z) coordinate sequences.

        Example
        -------

        >>> line = LineString([[0.0, 0.0], [1.0, 2.0]])
        >>> line = LineString(array([[0.0, 0.0], [1.0, 2.0]]))
        
        Each result in a line string from (0.0, 0.0) to (1.0, 2.0).
        """
        BaseGeometry.__init__(self)

        if coordinates is None:
            # allow creation of null lines, to support unpickling
            pass
        else:
            self._geom, self._ndim = geos_multipoint_from_py(coordinates)


    @property
    def __geo_interface__(self):
        return {
            'type': 'MultiPoint',
            'coordinates': tuple([g.coords[0] for g in self.geoms])
            }

    @property
    def ctypes(self):
        if not self._ctypes_data:
            temp = c_double()
            n = self._ndim
            m = len(self.geoms)
            array_type = c_double * (m * n)
            data = array_type()
            for i in xrange(m):
                g = self.geoms[i]._geom    
                cs = lgeos.GEOSGeom_getCoordSeq(g)
                lgeos.GEOSCoordSeq_getX(cs, 0, byref(temp))
                data[n*i] = temp.value
                lgeos.GEOSCoordSeq_getY(cs, 0, byref(temp))
                data[n*i+1] = temp.value
                if n == 3: # TODO: use hasz
                    lgeos.GEOSCoordSeq_getZ(cs, 0, byref(temp))
                    data[n*i+2] = temp.value
            self._ctypes_data = data
        return self._ctypes_data

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        return {
            'version': 3,
            'shape': (len(self.geoms), self._ndim),
            'typestr': '<f8',
            'data': self.ctypes,
            }

    @property
    def coords(self):
        raise NotImplementedError

    @property
    def geoms(self):
        return GeometrySequence(self, Point)
        

class MultiPointAdapter(MultiPoint):

    """Adapts a Python coordinate pair or a numpy array to the multipoint
    interface.
    """
    
    context = None

    def __init__(self, context):
        self.context = context

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0])

    @property
    def _geom(self):
        """Keeps the GEOS geometry in synch with the context."""
        return geos_multipoint_from_py(self.context)[0]       

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        try:
            return self.context.__array_interface__
        except AttributeError:
            return {
                'version': 3,
                'shape': (self._ndim,),
                'typestr': '<f8',
                'data': self.ctypes,
                }


def asMultiPoint(context):
    """Factory for MultiPointAdapter instances."""
    return MultiPointAdapter(context)

#_point = Point()
#
#def geos_point_factory(ob):
#    return _point._geos_from_py(ob)


# Test runner
def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

