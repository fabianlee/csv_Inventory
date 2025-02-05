#!/usr/bin/env python
# -*- coding:utf-8 -*-
# This module reads the CSV file and converts it into inventory information.
#
# Copyright (C) 2018 Masayuki Miyake
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http:#www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
This module reads the CSV file and converts it into inventory information.
"""

import csv
import yaml
import json
import sys

TYPE_STRING  = 'S'
TYPE_INTEGER = 'I'
TYPE_BOOLEAN = 'B'
TYPE_FLOAT   = 'F'

def load_csv_inventory(file_name):
    """
    Read inventory file in CSV format.

    :param string file_name: csv file name
    :rtype: array
    :return: node information array.
    """ 

    # load csv
    ret = []

    with open(file_name, 'r') as csv_file:
        reader = csv.reader(csv_file, dialect='excel')
        # load header
        header = next(reader)
        header_info = load_header(header)
        # load node information
        for row in reader:
            if len(row) <= 0:
                continue

            node_info = load_node_info(header_info, row)
            ret.append(node_info)

    return ret


def load_header(header):
    """
    Read header line.
    Returns an array of header information.
    header information format => [{"item_type": Type, "item_name": item name},...]
    ex. [{"item_type": "S", "item_name": "ansible_host"}, ...]

    :param array header: Element array of headers.
    :rtype: array
    :return: Array of header information.
    """ 

    ret = []

    for item in header:
        item = item.strip()
        elements = item.split('.')
        if len(elements) >= 2:
            # get item value type
            item_type = elements[0].strip()
            # get item name
            item_name = elements[1].strip()
            ret.append({'item_type': item_type, 'item_name': item_name})
        else:
            ret = None
            break

    return ret


def load_node_info(header_info_array, item_array):
    """
    Read node information line.
    Returns an dict of node information.
    node information format => {item_name1: value1, item_name2: value2, ...}
    ex. {"host_name": "web001", "port_no": 80, ... }

    :param array header_info_array: Array of .
    :param array item_array: Array of node information.
    :rtype: dict
    :return: Dict of node information.
    """ 

    ret = {}

    pos = 0
    for header in header_info_array:
        # get item value
        item = item_array[pos].strip()
        item_type = header['item_type']
        item_name = header['item_name']
        # convert value
        val = conv_str2value(item_type, item)
        if val is not None:
            ret[item_name] = val

        pos += 1

    return ret


def load_common_info(file_name):
    """
    Read node information line.
    Returns an dict of node information.
    node information format => {item_name1: value1, item_name2: value2, ...}
    ex. {"host_name": "web001", "port_no": 80, ... }

    :param string file_name: Name of common definition file in yaml format.
    :rtype: dict
    :return: Dict of common information.
    """ 

    ret = None
    with open(file_name, 'r') as common_file:
        ret = yaml.load(common_file,Loader=yaml.FullLoader)

    return ret


def conv_str2value(item_type, item):
    """
    Convert a character string to a specified data type.

    :param string item_type: A character string representing the type of item data.
    :param string item: Value of item data.
    :rtype: undecided
    :return: The converted value.
    """ 

    ret = None

    if len(item) <= 0:
        return None

    if TYPE_STRING == item_type:
        # set string value
        ret = item
    elif TYPE_INTEGER == item_type:
        # set integer value
        ret = int(item)
    elif TYPE_BOOLEAN == item_type:
        # set boolean value
        item = item.lower()
        if item == 'true':
            ret = True
        elif item == 'false':
            ret = False
        else:
            ret = False
    elif TYPE_FLOAT == item_type:
        # set float value
        ret = float(item)
    else:
        # set value
        ret = item

    return ret


def make_hostvars(node_info_array):
    """
    Generate hostvars from the node information array.

    :param array node_info_array: Node information array.
    :rtype: dict
    :return: Dictionary of hostvars.
    """ 

    ret = {}

    for node_info in node_info_array:
        #" get host_name
        host_name = node_info.pop('host_name', None)
        if host_name is None:
            ret = None
            break
        # make hostvar
        ret[host_name] = node_info

    return ret


def make_groups(hostvars):
    """
    Generate groups information from the hostvars.

    :param dict hostvars: hostvars.
    :rtype: dict
    :return: Dictionary of groups information.
    """ 

    ret = {}

    for node_name, node_info in hostvars.items():
        # get group name
        group_name = node_info.pop('group', None)
        if group_name is None:
            ret = None
            break
        # make groups
        if group_name in ret:
            group = ret[group_name]
            hosts = group['hosts']
            hosts.append(node_name)
        else:
            group = {}
            hosts = []
            hosts.append(node_name)
            group['hosts'] = hosts
            ret[group_name] = group

    return ret


def get_groupvars(common_info):
    """
    Extract groupvars from group information defined in common information.

    :param dict common_info: common information dictionary.
    :rtype: dict
    :return: groupvars dictionary.
    """ 

    ret = {}
    # get group_vars
    group_vars = common_info.pop('group_vars', None)
    if group_vars is not None: 
        for name, val in group_vars.items():
            ret[name] = val
    # get all vars
    all_vars = common_info.pop('all_vars', None)
    if all_vars is not None: 
        ret['all'] = all_vars

    return ret


def add_groupvars(groups, groupvars):
    """
    Register group common information from common information in the group information dictionary.

    :param dict groups: group information dictionary.
    :param dict groupvars: groupvars dictionary.
    """ 

    for name, val in groupvars.items():
        if name == 'all':
          groups['all'] = {'vars': val}
        else:
            if name in groups:
                groups[name]['vars'] = val


def make_specific_items(node_info_array, groupvars, spec_vars):
    """
    With this function, customize node information array.

    :param array node_info_array: node information array.
    :param dict groupvars: groupvars dictionary.
    :param dict spec_vars: specific values dictionary.
    :rtype: array
    :return: Customized node information array.
    """ 
    backend_array = []

    def_port_no = groupvars['web_server']['port_no']

    # make ha proxy backend information
    for node in node_info_array:
        group = node['group']
        if group == 'web_server':
            host_name = node['host_name']
            backend_ip = node['backend_ip']
            port_no = node.get('port_no', def_port_no)
            weight = node.get('weight', 1)
            backend = {'host_name': host_name, 'backend_ip': backend_ip, 
                       'port_no': port_no, 'weight': weight}
            backend_array.append(backend)

    # add web_backend
    haproxy_group = groupvars.get('ha_proxy', None)
    if haproxy_group is not None:
        haproxy_group['web_backend'] = backend_array


    return node_info_array


def main():
    """
    main function.

    """ 
    # load common information file
    common_info = load_common_info('common_val.yml')

    # load inventory file
    inv_list = common_info.pop('inventory_list', ['inventory.csv'])
    node_info_array = []
    for file_name in inv_list:
        # load 
        nodes = load_csv_inventory(file_name)
        if nodes is not None:
            node_info_array.extend(nodes)

    # get groupvars
    groupvars = get_groupvars(common_info)

    # make specific item
    specific_vars = common_info.pop('specific_vars', {})
    node_info_array = make_specific_items(node_info_array, groupvars, specific_vars)

    hostvars = make_hostvars(node_info_array)
    groups = make_groups(hostvars)

    # add groupvars
    add_groupvars(groups, groupvars)
    groups['_meta'] = {'hostvars': hostvars}

    # dump JSON format
    json.dump(groups, sys.stdout)


if __name__ == '__main__':

    main()

