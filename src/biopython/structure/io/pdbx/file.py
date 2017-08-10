# Copyright 2017 Patrick Kunzmann.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.

import shlex
import numpy as np
from ....file import File

class PDBxFile(File):
    
    def __init__(self):
        self._lines = []
        # This dictionary saves the PDBx category names,
        # together with its line position in the file
        # and the data_block it is in
        self._categories = {}
    
    
    def read(self, file_name):
        with open(file_name, "r") as f:
            str_data = f.read()
        self._lines = str_data.split("\n")
        # Remove emptyline at then end of file, if present
        if self._lines[-1] == "":
            del self._lines[-1]
        
        current_data_block = ""
        current_category = None
        start = -1
        stop = -1
        is_loop = False
        has_multiline_values = False
        for i, line in enumerate(self._lines):
            # Ignore empty and comment lines
            if not _is_empty(line):
                data_block_name = _data_block_name(line)
                if data_block_name is not None:
                    data_block = data_block_name
                    # If new data block begins, reset category data
                    current_category = None
                    start = -1
                    stop = -1
                    is_loop = False
                    has_multiline_values = False
                
                is_loop_in_line = _is_loop_start(line)
                category_in_line = _get_category_name(line)
                if is_loop_in_line or (category_in_line != current_category
                                       and category_in_line is not None):
                    # Start of a new category
                    # Add an entry into the dictionary with the old category
                    stop = i
                    self._add_category(data_block, current_category, start,
                                       stop, is_loop, has_multiline_values)
                    # Track the new category
                    if is_loop_in_line:
                        # In case of lines with "loop_" the category is in the
                        # next line
                        category_in_line = _get_category_name(self._lines[i+1])
                    is_loop = is_loop_in_line
                    current_category = category_in_line
                    start = i
                    has_multiline_values = False
                
                multiline = _is_multi(line, is_loop)
                if multiline:
                    has_multiline_values = True
        # Add the entry for the final category
        # Since at the end of the file the end of the category
        # is not determined by the start of a new one,
        # this needs to be handled separately
        stop = len(self._lines)
        self._add_category(data_block, current_category, start,
                           stop, is_loop, has_multiline_values)
    
    
    def get_block_names(self):
        blocks = []
        for category_tuple in self._categories.keys():
            block = category_tuple[0]
            if block not in blocks:
                blocks.append(block)
        return blocks
    
    
    def get_category(self, category, block=None):
        if block is None:
            block = self.get_block_names()[0]
        category_info = self._categories[(block, category)]
        start = category_info["start"]
        stop = category_info["stop"]
        is_loop = category_info["loop"]
        is_multilined = category_info["multiline"]
        
        if is_multilined:
            # Convert multiline values into singleline values
            pre_lines = [line.strip() for line in self._lines[start:stop]
                         if not _is_empty(line) and not _is_loop_start(line)]
            lines = (len(pre_lines)) * [None]
            # lines index
            k = 0
            # pre_lines index
            i = 0
            while i < len(pre_lines):
                if pre_lines[i][0] == ";":
                    # multiline values
                    lines[k-1] += " '" + pre_lines[i][1:]
                    j = i+1
                    while pre_lines[j] != ";":
                        lines[k-1] += pre_lines[j]
                        j += 1
                    lines[k-1] += "'"
                    i = j+1
                elif not is_loop and pre_lines[i][0] in ["'",'"']:
                    # Singleline values where value is in the line
                    # after the corresponding key
                    lines[k-1] += " " + pre_lines[i]
                    i += 1
                else:    
                    # Normal singleline value in the same row as the key
                    lines[k] = pre_lines[i]
                    i += 1
                    k += 1
            lines = [line for line in lines if line is not None]
            
        else:
            lines = [line.strip() for line in self._lines[start:stop]
                     if not _is_empty(line) and not _is_loop_start(line)]
        
        if is_loop:
            category_dict = self._process_looped(lines)
        else:
            category_dict = self._process_singlevalued(lines)
        
        return category_dict
            
    
    def set_category(self, category, category_dict, block=None, quote=True):
        if block is None:
            block = self.get_block_names()[0]
            
        if isinstance(list(category_dict.values())[0], np.ndarray):
            is_looped = True
        else:
            is_looped = False
            
        if quote:
            for key, value in category_dict.items():
                if is_looped:
                    for i in range(len(value)):
                        value[i] = shlex.quote(value[i])
                else:
                    category_dict[key] = shlex.quote(value)
        
        if is_looped:
            key_lines = ["_" + category + "." + key
                         for key in category_dict.keys()]
            value_arr = list(category_dict.values())
            # Array containing the number of characters + whitespace
            # of each column 
            col_lens = np.zeros(len(value_arr), dtype=int)
            for i, column in enumerate(value_arr):
                col_len = 0
                for value in column:
                    if len(value) > col_len:
                        col_len = len(value)
                # Length of column is max value length 
                # +1 whitespace character as separator 
                col_lens[i] = col_len+1
            arr_len = len(value_arr[0])
            value_lines = [""] * arr_len
            for i in range(arr_len):
                for j, arr in enumerate(value_arr):
                    value_lines[i] += arr[i] + " "*(col_lens[j] - len(arr[i]))
            new_lines = ["loop_"] + key_lines + value_lines
            
        else:
            # For better readability not only one space is inserted after each
            # key, but as much spaces that every value starts at the same
            # position in the line
            max_len = 0
            for key in category_dict.keys():
                if len(key) > max_len:
                    max_len = len(key)
            # "+3" Because of three whitespace chars after longest key
            req_len = max_len + 3
            new_lines = ["_" + category + "." + key
                         + " " * (req_len-len(key)) + value
                         for key, value in category_dict.items()]
            
        # A command line is set after every category
        new_lines += ["#"]
        
        if (block,category) in self._categories:
            # Category already exists in data block
            category_info = self._categories[(block, category)]
            # Insertion point of new lines
            old_category_start = category_info["start"]
            old_category_stop = category_info["stop"]
            category_start = old_category_start 
            # Difference between number of lines of the old and new category
            len_diff = len(new_lines) - (old_category_stop-old_category_start)
            # Remove old category content
            del self._lines[old_category_start : old_category_stop]
            # Insert new lines at category start
            self._lines[category_start:category_start] = new_lines
            # Update category info
            category_info["start"] = category_start
            category_info["stop"] = category_start + len(new_lines)
            # When writing a category no multiline values are used
            category_info["multiline"] = False
            category_info["loop"] = is_looped
        elif block in self.get_block_names():
            # Data block exists but not the category
            # Find last category in the block
            # and set start of new category to stop of last category
            last_stop = 0
            for category_tuple, category_info in self._categories.items():
                if block == category_tuple[0]:
                    if last_stop < category_info["stop"]:
                        last_stop = category_info["stop"]
            category_start = last_stop
            category_stop = category_start + len(new_lines)
            len_diff = len(new_lines)
            self._lines[category_start:category_start] = new_lines
            self._add_category(block, category, category_start, category_stop,
                               is_looped, is_multilined=False)
        else:
            # The data block does not exist
            # Put the begin of data block in front of new_lines
            new_lines = ["data_"+block, "#"] + new_lines
            # Find last category in the file
            # and set start of new data_block with new category
            # to stop of last category
            last_stop = 0
            for category_info in self._categories.values():
                if last_stop < category_info["stop"]:
                    last_stop = category_info["stop"]
            category_start = last_stop + 2
            category_stop = last_stop + len(new_lines)
            len_diff = len(new_lines)-2
            self._lines[last_stop:last_stop] = new_lines
            self._add_category(block, category, category_start, category_stop,
                               is_looped, is_multilined=False)
        # Update start and stop of all categories appearing after the
        # changed/added category
        for category_info in self._categories.values():
            if category_info["start"] > category_start:
                category_info["start"] += len_diff
                category_info["stop"] += len_diff
                
    
    def write(self, file_name):
        with open(file_name, "w") as f:
            f.writelines([line+"\n" for line in self._lines])
        
    
    
    def copy(self):
        pdbx_file = PDBxFile()
        pdbx_file._lines = copy.deepcopy(self._lines)
        pdbx_file._categories = copy.deepcopy(self._categories)
    
    
    def _add_category(self, block, category_name,
                      start, stop, is_loop, is_multilined):
        # Before the first category starts,
        # the current_category is None
        # This is checked before adding an entry
        if category_name is not None:
            self._categories[
                (block, category_name)] = {"start"     : start,
                                           "stop"      : stop,
                                           "loop"      : is_loop,
                                           "multiline" : is_multilined}
    
            
    def _process_singlevalued(self, lines):
        category_dict = {}
        for line in lines:
            parts = shlex.split(line)
            key = parts[0].split(".")[1]
            value = parts[1]
            category_dict[key] = value
        return category_dict
    
    
    def _process_looped(self, lines):
        category_dict = {}
        keys = []
        # Array index
        i = 0
        # Dictionary key index
        j = 0
        for line in lines:
            in_key_lines = (line[0] == "_")
            if in_key_lines:
                key = line.split(".")[1]
                keys.append(key)
                # Pessimistic array allocation
                # numpy array filled with strings
                category_dict[key] = np.zeros(len(lines),
                                              dtype=object)
                keys_length = len(keys)
            else:
                for value in shlex.split(line):
                    category_dict[keys[j]][i] = value
                    j += 1
                    if j == keys_length:
                        # If all keys have been filled with a value,
                        # restart with first key with incremented index
                        j = 0
                        i += 1
        for key in category_dict.keys():
            # Trim to correct size
            category_dict[key] = category_dict[key][:i]
        return category_dict
    

def _is_empty(line):
    return len(line) == 0 or line[0] == "#"


def _data_block_name(line):
    if line.startswith("data_"):
        return line[5:]
    else:
        return None

def _is_loop_start(line):
    return line.startswith("loop_")


def _is_multi(line, is_loop):
    if is_loop:
        return line[0] == ";"
    else:
        return line[0] in [";","'",'"']


def _get_category_name(line):
    if line[0] != "_":
        return None
    else:
        return line[1:line.find(".")]
    