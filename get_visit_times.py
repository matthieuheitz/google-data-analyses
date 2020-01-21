#!/usr/bin/env python
"""
get_visit_times.py

# My first attempt at digging into my location's data
# This scripts tells me all the dates and times when I have been somewhere specific.
# See below at USER INPUT, to change point of interest, and date boundaries
# Download your own Location History JSON file at https://takeout.google.com/settings/takeout

Author: Matthieu Heitz

"""




import json
import numpy as np
import datetime


# Helper functions
def date_ymd_to_timestamp_ms(y,m,d):
    return datetime.datetime(y,m,d).timestamp()*1e3


def deg2rad(a):
    return a*np.pi/180


def dist_btw_two_points(p1,p2):
    # p1 and p2 must be np.array([1,2])
    # Using https://en.wikipedia.org/wiki/Haversine_formula
    phi1 = deg2rad(p1[0])
    lba1 = deg2rad(p1[1])
    phi2 = deg2rad(p2[0])
    lba2 = deg2rad(p2[1])
    r = 6371*1e3    # Earth's radius: 6371kms in meters
    return 2*r*np.arcsin(np.sqrt(np.sin((phi2-phi1)/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin((lba2-lba1)/2)**2))


# LOAD DATA

json_file = "location_history.json"
# Read the file
print("Loading '%s' ..."%json_file)
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
positions = np.zeros([n,2])  # in degrees
# accuracy = np.zeros(n)      # don't know the unit
# activity = {}         # Don't store activity since we don't use it

for i in range(n):
    point = data[i]
    if 'timestampMs' in point:
        timestampMs[i] = float(point['timestampMs'])
    if ('latitudeE7' in point) and ('longitudeE7' in point):
        positions[i] = np.array([float(point['latitudeE7']),float(point['longitudeE7'])])/1e7
    # if 'accuracy' in point:
    #     accuracy[i] = point['accuracy']
    # if 'activity' in point:
    #     activity[i] = point['activity']

# n_act = len(activity.keys())
# print("Total number of points with activity: %d  (%0.1f%%)"%(n_act,int(n_act/n*100)))
print("Total number of points: %d"%n)

# Free some memory
data.clear()
main_dict.clear()

#############
# USER INPUT
#############

# Get first and last timestamps of interest
begin_ts = date_ymd_to_timestamp_ms(2018,9,1)
end_ts = date_ymd_to_timestamp_ms(2018,9,30)
# end_ts = timestampMs[-1]    # Last one

# Point of interest
poi = np.array([45.773944,4.890715])    # in degrees
radius_max = 50                         # in meters

# Define the interval of time below which timestamps should be grouped together
group_size = datetime.timedelta(weeks=0, days=0, hours=1, minutes=0, seconds=0, milliseconds=0)
# Amount of info to show about each group:
# 0: None
# 1: Number of points in group
# 2: Add point IDs, first/last datetime in group, avg dist to POI
group_verbosity = 1

####################
# END OF USER INPUT
####################

# Get time boundary index
begin_index = np.argmax(timestampMs >= begin_ts)
end_index = np.argmax(timestampMs >= end_ts)

# Get group_size in milliseconds
grpsMs =  group_size.total_seconds()*1000

# Get all points that are within radius_max of the poi
close_points = []
dist2poi = []
# Check positions only after the specified date.
for i in range(begin_index,end_index):
    # Compute distance to point of interest
    dist = dist_btw_two_points(poi, positions[i])
    if dist < radius_max:
        close_points.append(i)
        dist2poi.append(dist)

close_points = np.array(close_points)
print("Number of close points: %d"%close_points.size)

ts2datetime = lambda x: datetime.datetime.utcfromtimestamp(int(x/1e3)).strftime('%Y-%m-%d %H:%M:%S')

prev = 0    # Keeps in memory the last timestamp displayed
for i in range(close_points.size):
    # If the delta between timestamps is bigger than the group size, or if it's the beginning or the end.
    if timestampMs[close_points[i]]-timestampMs[close_points[prev]] > grpsMs or i == 0 or i == close_points.size-1:
        # If it's not the beginning and there are at least 2 points to make a group.
        if i>0 and i-prev > 2:
            if i == close_points.size-1: i=i+1
            if group_verbosity == 1:
                print("\tGroup of %d points"%(i-prev-2))
            if group_verbosity == 2:
                print("\tGroup of %d points: %d -> %d"%(i-prev-2,close_points[prev+1],close_points[i-1]))
                pt_date_im1 = ts2datetime(timestampMs[close_points[i-1]])
                pt_date_prevp1 = ts2datetime(timestampMs[close_points[prev+1]])
                print("\tFrom: %s"%pt_date_prevp1)
                print("\tTo  : %s"%pt_date_im1)
                print("\tMean dist to POI: %0.1fm"%np.mean(dist2poi[prev+1:i]))

        if group_verbosity == 2: print()    # Add space between lines
        # Else, display the point, unless it's the end
        if i != close_points.size:
            pt_date = ts2datetime(timestampMs[close_points[i]])
            print("Point %d  --  Date: %s  --  Distance to POI: %dm"%(close_points[i],pt_date,dist2poi[i]))
            prev = i
