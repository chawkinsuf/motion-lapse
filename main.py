#! /usr/bin/python
from __future__ import print_function
import time, os, sys, signal, threading, logging
import numpy, scipy, scipy.stats, scipy.misc, skimage
import Tkinter
import app.setup

from pprint import pprint
from path import path
from datetime import datetime
from PIL import Image, ImageTk


# Make a quick function to get the current time with microseconds
DATE_STR=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f")

# Generate the directory name for our images
IMAGE_DIR='capture/' + DATE_STR() + '/'


class ThreadData:
	def __init__( self ):
		self.lock = threading.Lock()
		self.image = None

	def new_image( self, image ):
		skipped = False
		with self.lock:
			if not self.image is None:
				skipped = True
			self.image = image
		if skipped is True:
			logging.warning( 'Frame skipped' )

	def get_image( self ):
		with self.lock:
			if self.image is None:
				return None
			image = self.image
			self.image = None
			return image


class VisionThread( threading.Thread ):
	def __init__( self, data, image_labels ):

		# Call the parent
		threading.Thread.__init__( self )

		# Store our data
		self.data = data

		# Store the previous image
		self.previous = None

		# Create our tk store
		self.imagetk = [ None ] * len( image_labels )

		# Store our labels
		self.image_labels = image_labels

	def run( self ):
		global exitmain
		while  exitmain is False:

			# Look for a new image
			image = self.data.get_image()

			# Process if we got it
			if not image is None:
				self.process( image )

			# Don't want to wait too long to process the next image
			time.sleep(0.01)

	def process( self, image ):

		# Status update
		logging.info('Image received by vision thread')

		# See how long our process takes
		start_time = time.time()

		# Convert the image to grayscale and normalize
		image = self.grayscale( image )
		image = self.normalize( image )

		if self.previous is None:
			self.previous = image
			return

		# Subtract the images
		diff = abs( image - self.previous )

		# Theshold the image so we only look at sufficiently different pixels
		thresh = scipy.stats.threshold( diff, threshmin=0.1, newval=0 )
		thresh = scipy.stats.threshold( thresh, threshmax=0.1, newval=1 )

		# Total the changed pixels
		total = scipy.sum( thresh )

		# Log the runtime
		end_time = time.time()

		color = '\033[1;32m' if ( total > 80 ) else '\033[1;31m'
		logging.info( 'Detected %s%d\033[0m changed pixels ' % ( color, total ) )
		logging.info( 'Processing time: \033[1;34m%.3f\033[0m ms' % ( 1000*(end_time - start_time) ) )

		# Show the images
		self.show_image( image, 0 )
		self.show_image( self.previous, 1 )
		self.show_image( diff, 2 )
		self.show_image( thresh, 3 )

		# Store the new image
		self.previous = image

	def show_image( self, image, index ):
		display = Image.fromarray( image * 255 )
		display = display.resize( (200, 150), Image.ANTIALIAS )
		self.imagetk[ index ] = ImageTk.PhotoImage( display )
		self.image_labels[ index ].configure( image = self.imagetk[ index ] )

	def grayscale( self, image ):
		global config, exitmain
		grayscale = config.get( 'ALGORITHM', 'grayscale' )

		if grayscale == 'average':
			return scipy.average( image, -1 ) / 255.

		elif grayscale == 'luminance':
			return color.rgb2gray( image )

		else:
			exitmain = True
			raise Exception( 'Invalid grayscale setting: %s' % grayscale )

	def normalize( self, image ):
		global config, exitmain
		normalize = config.get( 'ALGORITHM', 'normalize' )

		if normalize == 'minmax':
			max = image.max()
			min = image.min()
			return ( image - min) / ( max - min )

		elif normalize == 'std':
			return ( image - image.mean() ) / image.std()

		elif normalize == 'histogram':
			return skimage.exposure.equalize_hist( image )

		else:
			exitmain = True
			raise Exception( 'Invalid normalize setting: %s' % normalize )


class CaptureThread( threading.Thread ):
	def __init__( self, data ):

		# Call the parent
		threading.Thread.__init__( self )

		# Store our data
		self.data = data

		# Get the image list
		self.image_files = path('test-images').files('image*.jpg')
		self.image_files.sort( reverse = True )

	def run( self ):
		global exitmain
		while  exitmain is False:

			# Taking a picture
			logging.info('Capturing detection image')

			# Simulate time to take picture
			time.sleep(2)

			# Load the image
			filename = self.image_files.pop().abspath()
			logging.info( 'Showing image ' + filename )
			self.data.new_image( scipy.misc.imread( filename ) )

			# Yeild the thread
			time.sleep(0.1)


def maketk( root ):
	num_images = 4
	image_size = ( 200, 150 )
	root.geometry( '%dx%d' % tuple( 2*i for i in image_size ) )

	image_labels = []
	for i in range( num_images ):
		image_label = Tkinter.Label( root )
		image_label.place( x = ( i % 2 ) * image_size[0], y = ( i / 2 ) * image_size[1], width = image_size[0], height = image_size[1] )
		image_labels.append( image_label )

	return image_labels


def signal_handler( signalSent, frame ):
	global exitmain, original_handler
	exitmain = True
	logging.info( 'SIGINT caught' )
	logging.warning( 'Shutting down' )


def main():
	global exitmain, config, args

	# We just got started
	exitmain = False

	# Capture control-c presses
	signal.signal( signal.SIGINT, signal_handler )

	# Parse the command line args
	args = app.setup.args()

	# Setup the logger
	app.setup.log( args )

	# Process the config file
	config = app.setup.config( args )

	# Make a directory for our images
	os.makedirs( IMAGE_DIR )

	# Make our tkinter root and label
	root = Tkinter.Tk()
	image_labels = maketk( root )

	# Make our thread data
	data = ThreadData()

	# Create processing threads
	threads = [
		CaptureThread( data ),
		VisionThread( data, image_labels )
	]

	# Start the threads
	for thread in threads:
		thread.start()


	root.mainloop()
	exitmain = True


	# Wait for the user to send a SIGINT
	while exitmain is False:
		time.sleep(1)

	# Terminate the main thread
	logging.info('Main thread exiting')

	# Wait for our threads to exit cleanly
	for thread in threads:
		thread.join()


if __name__ == '__main__':
	main()



class InterruptHandler:

	def __init__(self, sig=signal.SIGINT):
		self.sig = sig

	def __enter__(self):

		self.interrupted = False
		self.released = False

		self.original_handler = signal.getsignal(self.sig)

		def handler(signum, frame):
			self.release()
			self.interrupted = True

		signal.signal(self.sig, handler)

		return self

	def __exit__(self, type, value, tb):
		self.release()

	def release(self):

		if self.released:
			return False

		signal.signal(self.sig, self.original_handler)

		self.released = True

		return True

# with GracefulInterruptHandler() as h:
# 	for i in xrange(1000):
# 		print "..."
# 		time.sleep(1)
# 		if h.interrupted:
# 			print "interrupted!"
# 			time.sleep(2)
# 			break