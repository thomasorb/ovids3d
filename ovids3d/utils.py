import numpy as np
import astropy.coordinates
from astropy import units as u

def xyz2sph(x, y, z):
    r = np.sqrt(x**2 + y**2 + z**2)
    phi = np.rad2deg(np.arctan2(y, x))
    theta = np.rad2deg(np.arccos(z/r))
    return r, theta, phi    

def sph2xyz(r, theta, phi):
    theta = np.deg2rad(theta)
    phi = np.deg2rad(phi)
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)
    return x, y, z


def to_lbd(coords):
    return np.array((coords.galactic.l.value,
                     coords.galactic.b.value,
                     coords.galactic.distance.value))

def norm(v):
    return v / np.sqrt(np.sum(v**2))

def compute_milky_way_hpr(ra, dec):
    """
    :param ra: ra in degrees
    :param dec: dec in degrees
    """
    DIFF = 5e-6
    DIST = 1 # object distance in kpc (unnecessary)
    

    origin_coords = astropy.coordinates.SkyCoord(
        ra=ra*u.degree, dec=dec*u.degree, distance=DIST*u.kpc)
    origin = to_lbd(origin_coords)
    
    # construct a vector which follows the RA axis in galactic coordinates
    x = norm(to_lbd(
        astropy.coordinates.SkyCoord(
            ra=(ra-DIFF)*u.degree, dec=dec*u.degree, distance=DIST*u.kpc)) - origin)
    
    roll = 180 - origin[0]
    pitch = -origin[1]
    heading = -(90-np.rad2deg(np.arccos(x[1])))
    print(heading, pitch, roll)
    return heading, pitch, roll

