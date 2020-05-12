# Python imports
import logging

# Libs
import geopandas as gpd
import pandas as pd
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
rgi_region = '15'  

# No need for a big map here
cfg.PARAMS['border'] = 80

# Local working directory (where OGGM will write its output)
WORKING_DIR = '/Users/louis/China_test/'
utils.mkdir(WORKING_DIR, reset=True)
cfg.PATHS['working_dir'] = WORKING_DIR

# RGI file
path = utils.get_rgi_region_file(rgi_region, version=rgi_version)
rgidf = gpd.read_file(path)

# Get the shapefile
basin = gpd.read_file('/Users/louis/china_test.shp')
print('got glacier shp')

# Take all glaciers in the desired areas
in_bas = [basin.geometry.contains(shpg.Point(x, y))[0] for
          (x, y) in zip(rgidf.CenLon, rgidf.CenLat)]
rgidf = rgidf.loc[in_bas]
print('found basins')
# Sort for more efficient parallel computing
rgidf = rgidf.sort_values('Area', ascending=False)
# Get rid of smaller glaciers
rgidf = rgidf.drop(rgidf[rgidf.Area < 0.5].index)
#Added in section to convert to pandas dataframe and print out file sol only need to run once
rgidf.to_file('/Users/louis/China_test/rgidf.shp')
#COnvert to pandas dataframe then print
rgipdf = pd.DataFrame(rgidf)
rgipdf.to_csv('/Users/louis/China_test/rgipdf.csv')

log.workflow('Starting OGGM run')
log.workflow('Number of glaciers: {}'.format(len(rgidf)))

# Go - get the pre-processed glacier directories
gdirs = workflow.init_glacier_directories(rgidf, from_prepro_level=4)

# We can step directly to a new experiment!
# Random climate representative for the recent climate (1985-2015)
# This is a kind of "commitment" run
workflow.execute_entity_task(tasks.run_random_climate, gdirs,
                             nyears=300, y0=2000, seed=1,store_monthly_step=True,
                             output_filesuffix='_commitment')
# Now we add a positive and a negative bias to the random temperature series
workflow.execute_entity_task(tasks.run_random_climate, gdirs,
                             nyears=300, y0=2000, seed=2,
                             temperature_bias=0.5,store_monthly_step=True,
                             output_filesuffix='_bias_p')
workflow.execute_entity_task(tasks.run_random_climate, gdirs,
                             nyears=300, y0=2000, seed=3,
                             temperature_bias=-0.5,store_monthly_step=True,
                             output_filesuffix='_bias_m')

# Write the compiled output
utils.compile_glacier_statistics(gdirs)
utils.compile_run_output(gdirs, input_filesuffix='_commitment')
utils.compile_run_output(gdirs, input_filesuffix='_bias_p')
utils.compile_run_output(gdirs, input_filesuffix='_bias_m')

# Log
m, s = divmod(time.time() - start, 60)
h, m = divmod(m, 60)
log.workflow('OGGM is done! Time needed: %d:%02d:%02d' % (h, m, s))
