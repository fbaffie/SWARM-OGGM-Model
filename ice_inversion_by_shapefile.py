# Python imports
import logging

# Libs
import geopandas as gpd
import shapely.geometry as shpg

# Locals
import oggm.cfg as cfg
from oggm import utils, workflow, tasks

# For timing the run
import time
start = time.time()

# Module logger
log = logging.getLogger(__name__)

# Initialize OGGM and set up the default run parameters
cfg.initialize(logging_level='WORKFLOW')
rgi_version = '61'
rgi_region = '15'  #

# Local working directory (where OGGM will write its output)
WORKING_DIR = '/Users/louis/China_test/'
utils.mkdir(WORKING_DIR, reset=True)
cfg.PATHS['working_dir'] = WORKING_DIR

# RGI file
path = utils.get_rgi_region_file(rgi_region, version=rgi_version)
rgidf = gpd.read_file(path)

## Get the shapefile
basin = gpd.read_file('/Users/louis/china_test.shp')
print('got glacier shp')

# Take all glaciers in the desired areas
in_bas = [basin.geometry.contains(shpg.Point(x, y))[0] for
          (x, y) in zip(rgidf.CenLon, rgidf.CenLat)]
rgidf = rgidf.loc[in_bas]
print('found basins')
# Get rid of smaller glaciers
rgidf = rgidf.drop(rgidf[rgidf.Area < 0.5].index)
# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)
print(rgidf)


log.workflow('Starting OGGM inversion run')
log.workflow('Number of glaciers: {}'.format(len(rgidf)))

# Go - get the pre-processed glacier directories
# We start at level 3, because we need all data for the inversion
gdirs = workflow.init_glacier_directories(rgidf,
                                          from_prepro_level=3,
                                          prepro_border=10)

# Default parameters


##### Where the stiffness parameters are set?
# Deformation: from Cuffey and Patterson 2010
glen_a = 2.4e-24
# Sliding: from Oerlemans 1997
fs = 5.7e-20

# Correction factors
factors = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
factors += [1.1, 1.2, 1.3, 1.5, 1.7, 2, 2.5, 3, 4, 5]
factors += [6, 7, 8, 9, 10]

# Run the inversions tasks with the given factors
for f in factors:
    # Without sliding
    suf = '_{:03d}_without_fs'.format(int(f * 10))
    workflow.execute_entity_task(tasks.mass_conservation_inversion, gdirs,
                                 glen_a=glen_a*f, fs=0)
    workflow.execute_entity_task(tasks.filter_inversion_output, gdirs)
    # Store the results of the inversion only
    utils.compile_glacier_statistics(gdirs, filesuffix=suf,
                                     inversion_only=True)

    # With sliding
    suf = '_{:03d}_with_fs'.format(int(f * 10))
    workflow.execute_entity_task(tasks.mass_conservation_inversion, gdirs,
                                 glen_a=glen_a*f, fs=fs)
    workflow.execute_entity_task(tasks.filter_inversion_output, gdirs)
    # Store the results of the inversion only
    utils.compile_glacier_statistics(gdirs, filesuffix=suf,
                                     inversion_only=True)

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.workflow('OGGM is done! Time needed: %d:%02d:%02d' % (h, m, s))
