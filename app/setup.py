from __future__ import print_function
import os, logging, argparse
from path import path
from ConfigParser import RawConfigParser


# Specify the default ini file
INI_FILE='~/.mlapse'

# Setup some text based log levels to use for input
LOG_LEVELS = { 'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARNING, 'error': logging.ERROR, 'critical': logging.CRITICAL }


# Parse command line arguments
def args():

	# Parse the arguments
	parser = argparse.ArgumentParser(description='Take some amazing timelaspse pictures')
	parser.add_argument('-t', '--testimages', default=None, help='Specify a set of images to use for testing')
	parser.add_argument('-i', '--inifile', default=INI_FILE, help='Set the location of the ini file')
	parser.add_argument('-f', '--inidefaults', action='store_true', help='Overwrite the specified ini file with the defaults')
	parser.add_argument('-ll', '--loglevel', default='warning', choices=LOG_LEVELS.keys(), help='Set the log level')
	parser.add_argument('-lf', '--logfile', default=None, type=argparse.FileType('w'), help='Write the log to a file instead of stdout')
	args = parser.parse_args()
	return args


# Parse the ini file
def config( args ):

	# Specify the defaults
	defaults = {
		'ALGORITHM': {
			'grayscale': 'average',		# average, luminance
			'normalize': 'minmax'		# minmax, std, histogram
		},
		'IMAGE': {
			'testWidth': 100,
			'testHeight': 75
		}
	}

	# Create the config object
	config = RawConfigParser()
	configfile = path( os.path.expanduser( args.inifile ) )

	# Write the defaults to file if no file exits
	if args.inidefaults or not configfile.isfile():

		# Parse the defauls
		for category, values in defaults.items():
			config.add_section( category )

			for key, value in values.items():
				config.set( category, key, value )

		# Write the file
		try:
			with configfile.open('w+') as pfile:
				config.write( pfile )

		except IOError:
			logging.warning('The default configuration could not be written to the ini file')

	# Otherwise we can read the file
	else:
		config.read( configfile )

	return config


# Setup the logging system
def log( args ):

	# Configure the logger
	loglevel = LOG_LEVELS[ args.loglevel ]
	logging.basicConfig( level=loglevel, stream=args.logfile, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S' )
