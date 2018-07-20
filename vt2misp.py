#!/usr/bin/python3

import re
import sys
import requests
import hashlib
import numbers
import json
import argparse
import pymisp
from pymisp import MISPObject
from pymisp import PyMISP
from pymisp import MISPEvent
from keys import misp_url, misp_key, misp_verifycert, vt_url, vt_key

def init(url, key):
    return PyMISP(misp_url, misp_key, misp_verifycert, 'json')

def create_objects(vt_results, event_dict):
    event = MISPEvent()
    event.from_dict(**event_dict)

    print ("- Creating objects")
    # Add VT Object
    detection = "%s/%s"% (vt_results['positives'],vt_results['total'])
    vt_comment = "File %s"% (vt_results['md5'])
    misp_object = event.add_object(name='virustotal-report', comment=vt_comment)
    obj_attr = misp_object.add_attribute('permalink', value=vt_results['permalink'])
    misp_object.add_attribute('detection-ratio', value=detection)
    misp_object.add_attribute('last-submission', value=vt_results['scan_date'])
    vt_obj_uuid = misp_object.uuid
    print ("\t* Permalink: " + vt_results['permalink'])
    print ("\t* Detection: " + detection)
    print ("\t* Last scan: " + vt_results['scan_date'] + "\r\n")

    # Add File Object
    misp_object = event.add_object(name='file')
    obj_attr = misp_object.add_attribute('md5', value=vt_results['md5'])
    misp_object.add_attribute('sha1', value=vt_results['sha1'])
    misp_object.add_attribute('sha256', value=vt_results['sha256'])
    misp_object.add_reference(vt_obj_uuid, 'analysed-with', 'Expanded with virustotal data')
    print ("\t* MD5: " + vt_results['md5'])
    print ("\t* SHA1: " + vt_results['sha256'])
    print ("\t* SHA256: " + vt_results['sha256'])

    try:
        # Submit the File and VT Objects to MISP
        misp.update(event)
    except (KeyError, RuntimeError, TypeError, NameError):
        print ("An error occoured when updating the event")
        sys.exit()

    print ("- The MISP objects seems to have been added correctly to the event.... ")

def vt_query(resource_value):
    params = {'apikey': vt_key, 'resource': resource_value, 'allinfo': '1'}
    headers = {
      "Accept-Encoding": "gzip, deflate",
      "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
    }
    response = requests.get(vt_url,
      params=params, headers=headers)
    json_response = response.json()
    if(json_response['response_code'] == 1):
        return(json_response)
    else:
        print ("Quitting -> The artifact was currently not present on VT")
        sys.exit()
    print ("- The artefact was found on Virustotal")

def is_in_misp_event(misp_event):
    found = False
    for obj_loop in misp_event['Object']:
        for attr_loop in obj_loop['Attribute']:
            if(attr_loop['value'] == args.checksum):
                found = True
    return(found)

def splash():
    print ('Virustotal to MISP')
    print ('(c)2018 eCrimeLabs')
    print ('https://www.ecrimelabs.com')
    print ('----------------------------------------')
    print ('')

if __name__ == '__main__':
    splash()
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--checksum", help="The checksum value has to be MD5, SHA-1 or SHA-256 for checking on VT")
    parser.add_argument("-u", "--uuid", help="The UUID of the event in MISP")
    args = parser.parse_args()
    if re.fullmatch("(([a-fA-F0-9]{64})|([a-fA-F0-9]{40})|([a-fA-F0-9]{32}))", args.checksum, re.VERBOSE | re.MULTILINE):
        print ("- Checking if checksum is valid - true")
    else:
    	# Match attempt failed
        print ("Quitting -> No Checksum detected - values has to be md5, sha1 or sha256")
        sys.exit()
    if re.fullmatch(r"([a-fA-F0-9\-]{36})", args.uuid, re.VERBOSE | re.MULTILINE):
        # 5b51eadd-7e9c-4015-b49c-3df79f590eb0
        print ("- Checking if UUID is valid - true")
    else:
    	# Match attempt failed
        print ("Quitting -> The UUID was not in a valid format")
        sys.exit()
    misp = init(misp_url, misp_key)
    misp_event = misp.get_event(args.uuid)['Event']

    # Check if Event with that UUID exists in the MISP instance
    try:
        misp_id = misp_event['id']
    except (KeyError, RuntimeError, TypeError, NameError):
        print ("Quitting -> The MISP UUID you entered does not exists on the MISP instance.")
        sys.exit()
    print ('- UUID for MISP event detected')

    if (is_in_misp_event(misp_event)):
        print ('Quitting -> Checksum ' + args.checksum + ' allready exists on event')
        sys.exit()
    else:
        print ('- Checksum ' + args.checksum + ' was not detected in the event')

    vt_data = vt_query(args.checksum)
    create_objects(vt_data, misp_event)
