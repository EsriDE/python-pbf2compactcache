# -------------------------------------------------------------------------------
# Name:        pbf2compactcache
# Purpose:     Build compact cache V2 bundles from pbfs in {x}/{y}/{z} structure
#
# Author:      luci6974
#
# Created:     20/09/2016
# Modified:    04/05/2018,esristeinicke
#              23/10/2019,mimo
#              15/05/2025,karschmidt
#
#  Copyright 2016 Esri
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.?
#
# -------------------------------------------------------------------------------
#
# Converts pbfs files to the esri Compact Cache V2 format
#
# Takes two arguments, the first one is the input {x} folder
# the second one being the output cache folder (tile)
#
#
# Assumes that the input folders are named 0 through x.

# Loops over columns and then row, in the order given by os.walk
# Keeps one bundle open in case the next tile fits in the same bundle
# In most cases this combination results in good performance
#
# It does not check the input tile format, and assumes that all
# the files are valid pbfs.  In other
# words, make sure there are no spurious files and folders under the input
# path, otherwise the output bundles might have strange content.
#
# -------------------------------------------------------------------------------
#

import argparse
import os
import struct
import shutil
import io
import re


# Bundle linear size in tiles
BSZ = 128
# Tiles per bundle
BSZ2 = BSZ ** 2
# Index size in bytes
IDXSZ = BSZ2 * 8

# Output path
output_path = None

# The curr_* variable are used for caching of open output bundles
# current bundle is kept open to reduce overhead
# TODO: Eliminate global variables
curr_bundle = None
# A bundle index list
# Array would be better, but it lacks 8 byte int support
curr_index = None
# Bundle file name without path or extension
curr_bname = None
# Current size of bundle file
# curr_offset = long(0)
curr_offset = int(0)
# max size of a tile in the current bundle
curr_max = 0


def get_arguments():
    """
    Parses commandline arguments.

    :return: commandline arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--source',
                        help='Input folder containing the root folders.', required=True)
    parser.add_argument('-d', '--destination',
                        help='Output for level folders.', required=True)
    parser.add_argument('-l', '--level',
                        help='Maximum level to process', required=True, type=int)

    # Return the command line arguments.
    arguments = parser.parse_args()

    # validate folder parameters
    if not os.path.exists(arguments.source):
        parser.error("Input folder does not exist or is inaccessible.")
    if not os.path.exists(arguments.destination):
        parser.error("Output folder does not exist or is inaccessible.")
    # validate level parameter
    if not arguments.level:
        parser.error("Please specifiy a maximum zoom level to process")

    return arguments


def init_bundle(file_name):
    """Create an empty V2 bundle file
    :param file_name: bundle file name
    """
    fd = open(file_name, "wb")
    # Empty bundle file header, lots of magic numbers
    header = struct.pack("<4I3Q6I",
                         3,  # Version
                         BSZ2,  # numRecords
                         0,  # maxRecord Size
                         5,  # Offset Size
                         0,  # Slack Space
                         64 + IDXSZ,  # File Size
                         40,  # User Header Offset
                         20 + IDXSZ,  # User Header Size
                         3,  # Legacy 1
                         16,  # Legacy 2
                         BSZ2,  # Legacy 3
                         5,  # Legacy 4
                         IDXSZ  # Index Size
                         )
    fd.write(header)
    # Write empty index.
    fd.write(struct.pack("<{}Q".format(BSZ2), *((0,) * BSZ2)))
    fd.close()


def cleanup():
    """
    Updates header and closes the current bundle
    """
    global curr_bundle, curr_bname, curr_index, curr_max, curr_offset
    curr_bname = None

    # Update the max rec size and file size, then close the file
    if curr_bundle is not None:
        curr_bundle.seek(8)
        curr_bundle.write(struct.pack("<I", curr_max))
        curr_bundle.seek(24)
        curr_bundle.write(struct.pack("<Q", curr_offset))
        curr_bundle.seek(64)
        curr_bundle.write(struct.pack("<{}Q".format(BSZ2), *curr_index))
        curr_bundle.close()

        curr_bundle = None


def open_bundle(row, col):
    """
    Make the bundle corresponding to the row and col current
    """
    global curr_bname, curr_bundle, curr_index, curr_offset, output_path, curr_max
    # row and column of top-left tile in the output bundle
    # start_row = (row / BSZ) * BSZ
    start_row = int((row / BSZ)) * BSZ
    # start_col = (col / BSZ) * BSZ
    start_col = int((col / BSZ)) * BSZ
    bname = "R{:04x}C{:04x}".format(start_row, start_col)
    # bname = "R%(r)04xC%(c)04x" % {"r": start_row, "c": start_col}

    # If the name matches the current bundle, nothing to do
    if bname == curr_bname:
        return

    # Close the current bundle, if it exists
    cleanup()

    # Make the new bundle current
    curr_bname = bname
    # Open or create it, seek to end of bundle file
    fname = os.path.join(output_path, bname + ".bundle")

    # Create the bundle file if it didn't exist already
    if not os.path.exists(fname):
        init_bundle(fname)

    # Open the bundle
    curr_bundle = open(fname, "r+b")
    # Read the current max record size
    curr_bundle.seek(8)
    curr_max = int(struct.unpack("<I", curr_bundle.read(4))[0])
    # Read the index as longs in a list
    curr_bundle.seek(64)
    curr_index = list(struct.unpack("<{}Q".format(BSZ2),
                                    curr_bundle.read(IDXSZ)))
    # Go to end
    curr_bundle.seek(0, os.SEEK_END)
    curr_offset = curr_bundle.tell()


def add_tile(pbf_file, row, col=None):
    """
    Add this tile to the output cache

    :param pbf_file: input tile as pbf
    :param row: row number
    :param col: column number
    """
    global BSZ, curr_bundle, curr_max, curr_offset

    # Read the tile data
    with open(pbf_file, 'rb') as byte_buffer_inter:
        byte_buffer = byte_buffer_inter.read()
        tile = io.BytesIO(byte_buffer).getvalue()
        tile_size = len(tile)

        # Write the tile at the end of the bundle, prefixed by size
        open_bundle(row, col)
        curr_bundle.write(struct.pack("<I", tile_size))
        curr_bundle.write(tile)
        # Skip the size
        curr_offset += 4

        # Update the index, row major
        curr_index[(row % BSZ) * BSZ + col % BSZ] = curr_offset + (tile_size << 40)
        curr_offset += tile_size

        # Update the current bundle max tile size
        curr_max = max(curr_max, tile_size)


def main(arguments):
    global output_path

    # parse parameter
    pbf_tile_folder = arguments.source
    cache_output_folder = arguments.destination
    max_level = arguments.level

    # loop through all level folders
    for root, dirs, files in os.walk(pbf_tile_folder):
        # sort the list of files numerical
        for pbf in sorted([x for x in dirs if x.isdecimal()]):
            # construct level folder name from folder
            level = 'L' + '{:02d}'.format(int(os.path.splitext(os.path.basename(pbf))[0]))
            level_folder = os.path.join(cache_output_folder, level)
            # get the level as int
            level_int = int(os.path.splitext(os.path.basename(pbf))[0])
            output_path = level_folder

            # create level folder if not exists
            if not os.path.exists(level_folder) and level_int <= max_level:
                os.makedirs(level_folder)
            else:
                # if exists, clean it up
                for sub_root, sub_dirs, sub_files in os.walk(level_folder):
                    for sub_dir in sub_dirs:
                        shutil.rmtree(sub_dir)
                    for sub_file in sub_files:
                        os.remove(os.path.join(sub_root, sub_file))

            # walk through folders and get subfolders and .pbf files
            folders_contents = {}
            for root, dirs, files in os.walk((os.path.join(pbf_tile_folder, pbf))):
                # check for max level
                if int(pbf) <= max_level:
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        folders_contents[dir_path] = os.listdir(dir_path)
                break
            for column in folders_contents:
                column_val = re.findall(r'\d+', column)[-1]
                for row in folders_contents[column]:
                    row_val = re.findall(r'\d+', row)[0]
                    add_tile(os.path.join(column, row), int(row_val), int(column_val))

           
            # cleanup open bundles
            cleanup()
            # Print finished level
            if int(pbf) <= max_level:
                print("Finished processing level {0}".format(pbf))
        break


if __name__ == '__main__':
    main(get_arguments())