#!/usr/bin/env python3
"""
get_visit_times.py

# My first attempt at digging into my location's data
# This scripts tells me all the dates and times when I have been somewhere specific.
# See below at USER INPUT, to change point of interest, and date boundaries
# Download your own Location History JSON file at https://takeout.google.com/settings/takeout

Author: Matthieu Heitz

"""

import argparse
import json
import numpy as np
import datetime
import sys
import os
from dateutil.parser import parse


# Helper functions
# def date_ymd_to_timestamp_ms(y, m, d):
#     return datetime.datetime(y, m, d).timestamp()*1e3


def deg2rad(a):
    return a*np.pi/180


def dist_btw_two_points(p1, p2):
    # p1 and p2 must be np.array([1,2])
    # Using https://en.wikipedia.org/wiki/Haversine_formula
    phi1 = deg2rad(p1[0])
    lba1 = deg2rad(p1[1])
    phi2 = deg2rad(p2[0])
    lba2 = deg2rad(p2[1])
    r = 6371*1e3    # Earth's radius: 6371kms in meters
    return 2*r*np.arcsin(np.sqrt(np.sin((phi2-phi1)/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin((lba2-lba1)/2)**2))


def find_points(**inputs):
    #############
    # USER INPUT
    #############

    # Get first and last timestamps of interest
    # begin_ts = date_ymd_to_timestamp_ms(2019, 1, 1)
    # end_ts = date_ymd_to_timestamp_ms(2019, 12, 31)
    # end_ts = timestampMs[-1]    # Last one

    # Convert `datetime` object to timestamp.
    begin_ts = inputs['start_date'].timestamp() * 1e3
    end_ts = inputs['end_date'].timestamp() * 1e3

    # Point of interest
    poi = np.array([inputs['lat'], inputs['lon']])    # in degrees
    radius_max = inputs['rad']                         # in meters

    # Define the interval of time below which timestamps should be grouped together
    group_size = datetime.timedelta(
        weeks=0, days=0, hours=1, minutes=0, seconds=0, milliseconds=0)
    # Amount of info to show about each group:
    # 0: None
    # 1: Number of points in group
    # 2: Add point IDs, first/last datetime in group, avg dist to POI
    group_verbosity = inputs['verbosity']

    # LOAD DATA

    json_file = inputs['in_file']
    # Read the file
    print("Loading '%s' ..." % json_file)
    main_dict = json.load(open(json_file))   # This can take a bit of time
    print("JSON file loaded")
    # data is a big list of dicts.
    data = main_dict['locations']
    n = len(data)   # Number of timesteps

    # Discovery of the dataset
    # # Some dicts only contain basic info : timestamp, latitude, longitude and accuracy
    # print(data[0])
    # # Others also have an activity :
    # print(data[300])
    #
    # # It seems that the list is ordered by timestamp.
    #
    # # More recent points have more info :
    # print(data[-1])

    # Build arrays of basic data
    print("Extracting relevant data...")
    timestampMs = np.zeros(n)   # in milliseconds
    positions = np.zeros([n, 2])  # in degrees
    accuracy = np.zeros(n)      # don't know the unit
    # activity = {}         # Don't store activity since we don't use it

    for i in range(n):
        point = data[i]
        if 'timestampMs' in point:
            timestampMs[i] = float(point['timestampMs'])
        if ('latitudeE7' in point) and ('longitudeE7' in point):
            positions[i] = np.array(
                [float(point['latitudeE7']), float(point['longitudeE7'])])/1e7
        if 'accuracy' in point:
            accuracy[i] = point['accuracy']
        # if 'activity' in point:
        #     activity[i] = point['activity']

    # n_act = len(activity.keys())
    # print("Total number of points with activity: %d  (%0.1f%%)"%(n_act,int(n_act/n*100)))
    print("Total number of points: %d" % n)

    # Free some memory
    data.clear()
    main_dict.clear()

    ####################
    # END OF USER INPUT
    ####################

    # Converter

    def ts2datetime(x): return datetime.datetime.utcfromtimestamp(
        int(x/1e3)).strftime('%Y-%m-%d %H:%M:%S')

    # Get time boundary index
    # np.searchsorted is a fast way to find the first element that is larger than the threshold. 1 is for True
    begin_index = np.searchsorted(timestampMs >= begin_ts, 1)
    end_index = np.searchsorted(timestampMs >= end_ts, 1)

    # Get group_size in milliseconds
    grpsMs = group_size.total_seconds()*1000

    # Get all points that are within radius_max of the poi
    close_points = []
    dist2poi = []
    # Check positions only after the specified date.
    for i in range(begin_index, end_index):
        # Compute distance to point of interest
        dist = dist_btw_two_points(poi, positions[i])
        if dist < radius_max:
            close_points.append(i)
            dist2poi.append(dist)

    close_points = np.array(close_points)
    print("Number of close points: %d\n" % close_points.size)

    prev = 0    # Keeps in memory the last timestamp displayed
    for i in range(close_points.size):
        # If the delta between timestamps is bigger than the group size, or if it's the beginning or the end.
        if timestampMs[close_points[i]]-timestampMs[close_points[prev]] > grpsMs or i == 0 or i == close_points.size-1:
            # If it's not the beginning and there are at least 2 points to make a group.
            if i > 0 and i-prev > 2:
                if i == close_points.size-1:
                    i = i+1
                if group_verbosity == 1:
                    print("\tGroup of %d points" % (i-prev-2))
                if group_verbosity == 2:
                    print("\n\tGroup of %d points: %d -> %d" %
                          (i-prev-2, close_points[prev+1], close_points[i-1]))
                    pt_date_im1 = ts2datetime(timestampMs[close_points[i-1]])
                    pt_date_prevp1 = ts2datetime(
                        timestampMs[close_points[prev+1]])
                    print("\tFrom: %s" % pt_date_prevp1)
                    print("\tTo  : %s" % pt_date_im1)
                    print("\tMean dist to POI: %0.1fm\n" %
                          np.mean(dist2poi[prev+1:i]))

            # if group_verbosity == 2: print()    # Add space between lines
            # Else, display the point, unless it's the end
            if i != close_points.size:
                pt_date = ts2datetime(timestampMs[close_points[i]])
                print("Point %d  --  Date: %s  --  Distance to POI: %dm" %
                      (close_points[i], pt_date, dist2poi[i]))
                prev = i


# Add CLI componets


def get_date(date_str):
    '''Converts a date string to a `datetime` object'''
    try:
        str_date = parse(date_str)
        return str_date
    except ValueError:
        sys.exit('Invalid date string provided: {}'.format(date_str))


def validate_inputs(**kwargs):
    '''Validate input parameters'''

    validated = {}

    validated['lat'] = float(kwargs['lat'])
    validated['lon'] = float(kwargs['lon'])
    validated['rad'] = float(kwargs['rad'])

    # Check if input file exists
    if os.path.exists(kwargs['in_file']):
        validated['in_file'] = kwargs['in_file']
    else:
        sys.exit("Can't location history file: {}".format(args['in_file']))

    # Validate start & end dates
    validated['start_date'] = get_date(kwargs['start_date'])
    if kwargs['end_date']:
        validated['end_date'] = get_date(kwargs['end_date'])
    else:
        validated['end_date'] = validated['start_date'] + \
            datetime.timedelta(days=1)

    if validated['end_date'] < validated['start_date']:
        sys.exit('End date must be after start date')

    # Validate output verbosity
    if int(kwargs['verbosity']) in range(3):
        validated['verbosity'] = int(kwargs['verbosity'])
    else:
        sys.exit("Invalid verbosity setting: {}".format(kwargs['verbosity']))
    print(validated)

    return validated


def get_arg_parser():
    parser = argparse.ArgumentParser(
        description='Search Google Maps location history')
    parser.add_argument("--lat", dest="lat", required=True,
                        help="POI latitude")
    parser.add_argument("--lon", dest="lon", required=True,
                        help="POI longitude")
    parser.add_argument('--start-date', dest='start_date', required=True,
                        help='Date to start downloading logs from')
    parser.add_argument('--end-date', dest='end_date',
                        help='End of date range. (default: 1 day after start-date)')
    parser.add_argument("-r", dest="rad",
                        help="Geofence radius (m)")
    parser.add_argument('-v', dest='verbosity',
                        help='Output verbosity (0, 1, or 2). Default: 0')
    parser.add_argument("-i", "--input", dest="in_file",
                        help="Path to location history file. (Default: location_history.json)")

    parser.set_defaults(in_file="location_history.json")
    parser.set_defaults(rad=100)
    parser.set_defaults(verbosity=1)

    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    my_args = validate_inputs(**args.__dict__)
    find_points(**my_args)


if __name__ == "__main__":
    main()
