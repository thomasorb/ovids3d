# Ovids3d


## Installation

This will create a environmenet called `video` with all the necessary packages.

```bash
conda create -n video -c conda-forge numpy scipy matplotlib astropy panda3d
```

clone [Ovids3D](https://github.com/thomasorb/orb)
```bash
cd
mkdir ovids3d-stable # this is an example and the folder can be the one you wish (but the following lines must be changed accordingly)
cd ovids3d-stable
git clone https://github.com/thomasorb/ovids3d.git
conda activate video # you don't need to do it if you are already in the video environment
python setup.py install 
```

To update the code:
```bash
cd ovids3d-stable # go the the installation folder you created initially
git pull # update the code
conda activate video 
python setup.py install 
```


## Quick start guide

[Quick Start Guide](docs/quick_start.md)
