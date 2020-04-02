# Dependencies
import xml.etree.ElementTree as ET
import pandas as pd
import openpyxl

# Setup ElementTree
tree = ET.parse('data/Thailand_Dives.ssrf')
root = tree.getroot()


#####################################
## Functions to be used in Program ##
#####################################

# Function to determine which keys should be saved
def insertKeyValues(dictionary):
    d = {}

    # Keys to not include
    delete = ['rating','visibility','size','workpressure','description','model','last-manual-time','tags','depth']

    # Make sure correct values are stored
    for k, v in dictionary:
        if k not in delete:
            d[replaceKey(k)] = v

    return d

# Function to replace the key with the wanted key
def replaceKey(k):
    # All keys that need their name replaced
    keyChange = {
        'start':'start_pressure',
        'end':'end_pressure',
        'air': 'air_temp',
        'water': 'water_temp',
        'divesiteid':'uuid'
    }

    if k in keyChange.keys():
        return keyChange[k]
    else:
        return k

# Take in duration column and make it into an int
def createMinutes(series, splitV):
    ls = []

    for i in dfMerged['duration']:
        sp = i.split(splitV) #split string at based on determined string
        ls.append(int(sp[0])) #save first index as int

    return ls

# Function to return dictionary with all wildlife in it
def wildlifeDict (listOfStrings):
    cleaned = []

    # Strip trailing spaces
    for l in listOfStrings:
        cleaned.append(l.rstrip())

    # Save indexes for fish and coral so we can compare which came first
    if 'Fish:' in cleaned:
        fish = cleaned.index('Fish:')
    else: fish = 0
    if 'Coral:' in cleaned:
        coral = cleaned.index('Coral:')
    else: coral = 0

    # See which value is higher and save all subsequent lines as a string
    if fish>0 and coral > fish:
        return wildlifeString(cleaned,fish,coral)
    elif coral>0 and fish > coral:
        return wildlifeString(cleaned,coral,fish)
    else: # if neither exists
        return {}

# Function to breakdown wildlife strings and separate them into fish or coral
def wildlifeString (listOfStrings, firsti, secondi):
    d = {}
    ls1 = []
    ls2 = []

    # What to do with the first value (which is the larger one)
    for i in range(firsti+1, secondi-1):
        # If there is a break, stop loop
        if listOfStrings[i] == '':
            break

        # add items to list
        else:
            ls1.append(listOfStrings[i])

        # add list to dict as joint string
        d[listOfStrings[firsti]] = ', '.join(ls1)


    # What to do with the lower value
    for i in range(secondi+1, len(listOfStrings)):

        # If there is a break, stop loop
        if listOfStrings[i] == '':
            break

        # add items to list
        else:
            ls2.append(listOfStrings[i])

        # add list to dict as joint string
        d[listOfStrings[secondi]] = ', '.join(ls2)

    # Return dictionary
    return(d)


########################################################
## Initial SSRF parse and Resulting Dict Organization ##
########################################################

# Create list of all site info
sites = [child.attrib for child in root[1]] # root 1 has site details

# Get all site info
dives = []
for dive in root[2]: # root 2 has dive details
    # Create dictionary for the dive
    details = {}

    # Save keys for the attributes of the dive element itself
    details.update(insertKeyValues(dive.attrib.items()))

    # Subelement breakdown
    for d in dive:

        # Save information based on where it's stored in tree
        if d.tag in ['divemaster','buddy','notes','suit']:
            details[d.tag] = d.text

        else:
            # Save keys for subelements
            details.update(insertKeyValues(d.attrib.items()))

            # Save subelement child for Depth
            if d.tag == 'divecomputer':
                details['max_depth'] = d[0].attrib['max']

    # Appened details to list
    dives.append(details)


#########################################
## DataFrame Creation and Organization ##
#########################################

# Create DF's from dictionaries
dfDive = pd.DataFrame(dives)
dfDive['number'] = pd.to_numeric(dfDive["number"])

dfSite = pd.DataFrame(sites)
dfSite.columns = ['uuid', 'site', 'gps'] #Rename columns

# Merge DFs and sort by dive number
dfMerged = pd.merge(dfDive, dfSite, on='uuid', how='outer')
dfMerged = dfMerged.sort_values(by=['number'])
dfMerged = dfMerged.reset_index(drop=True)

# Make duration int
dfMerged['duration_min'] = createMinutes(dfMerged['duration'],':')

# Drop UUID and original duration column
dfMerged = dfMerged.drop(['uuid'], axis=1)
dfMerged = dfMerged.drop(['duration'], axis=1)

# Reorder columns
dfMerged = dfMerged[['number', 'date', 'time', 'site', 'gps', 'duration_min',
         'max_depth', 'divemaster', 'buddy', 'suit', 'weight', 'start_pressure',
         'end_pressure', 'air_temp', 'water_temp', 'notes']]

# Select only rows that have more than 5 minute duration
dfSelected = dfMerged.loc[dfMerged['duration_min'] > 5]
dfSelected.head()


#########################################################
## Parse Notes Column Breaking it Down into Components ##
#########################################################

# Parse notes and save them to list
allNotes = []
for notes in dfSelected['notes']:

    d = {}

    # split string into
    notes = notes.split('\n')

    # First line is always shop information
    d['shop'] = notes[0]

    # Find viz and current information in list
    i = 1
    while i < len(notes):
        if 'Current: ' in notes[i]:
            d['current'] = notes[i].split('Current: ')[1]

        if 'Viz: ' in notes[i]:
            d['viz'] = notes[i].split('Viz: ')[1]

        i += 1

    # Get all wildlife information
    d.update(wildlifeDict(notes))

    # Append to all notes list
    allNotes.append(d)

# Create DF from notes
dfNote = pd.DataFrame(allNotes)
dfNote.columns = ['shop', 'current', 'viz', 'fish', 'coral']


#############################################
## Create and Save Final Cleaned DataFrame ##
#############################################

# merge dfSelected with dfNote, drop and reorganize
df = pd.merge(dfSelected, dfNote, left_index=True, right_index=True)
df = df.drop(['notes'], axis=1)
df = df[['number', 'date', 'time',
       'shop', 'divemaster', 'buddy', 'suit', 'weight', 'site',
       'gps', 'duration_min', 'max_depth', 'start_pressure',
       'end_pressure', 'air_temp', 'water_temp', 'current', 'viz',
       'fish', 'coral']]

# Save DF to excel
df.to_excel('dives_thailand.xlsx', sheet_name='dives')
