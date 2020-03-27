import numpy as np

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
    
