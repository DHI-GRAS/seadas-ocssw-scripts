"""
Routines to parse file metadata.

"""
import tarfile

import modules.DictUtils as du
import os
import re
import subprocess
import sys

def get_hdf4_content(filename):
    """
    Returns the header content from an HDF 4 file, which is obtained via
    'hdp dumpsds'.
    """
    # does executable exist?
    hdp = os.path.join(os.getenv('LIB3_BIN'), 'hdp')
    if not (os.path.isfile(hdp) and os.access(hdp, os.X_OK)):
        print(hdp, "is not executable.")
        return None

    # dump file header
    cmd = [hdp, 'dumpsds', '-h', '-s', filename]
    hdp_data = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    contents = hdp_data.read().decode("utf-8")
    return contents

def get_hdf5_header_plaintext(filename):
    """
    Returns the header content plain text from an HDF 5 file which is obtained via
    'h5dump -H'.
    """
    h5dump = os.path.join(os.getenv('LIB3_BIN'), 'h5dump')
    if not (os.path.isfile(h5dump) and os.access(h5dump, os.X_OK)):
        print(h5dump, "is not executable.")
        return None
    cmd = [h5dump, '-H', filename]
    h5dump_output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE).stdout
    content = h5dump_output.read().decode("utf-8")
    if content.find('HDF') != -1:
        return content
    else:
        return None

def get_hdf5_header_xml(filename):
    """
    Returns the header content as XML from an HDF 5 file which is obtained via
    'h5dump -Au'.
    """
    h5dump = os.path.join(os.getenv('LIB3_BIN'), 'h5dump')
    if not (os.path.isfile(h5dump) and os.access(h5dump, os.X_OK)):
        print(h5dump, "is not executable.")
        return None

    # dump file header
    cmd = [h5dump, '-A', '-u', filename]
    h5dump_output = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE).stdout
    content = h5dump_output.read().decode("utf-8")
    if content.find('HDF') != -1:
        return content
    else:
        return None

def get_mime_data(filename):
    """
    Returns the mime data for the file named in filename as found by running
    the file command
    """
    mimecmd = ['file', '--brief', filename]
    mime_data = subprocess.Popen(mimecmd,
                                 stdout=subprocess.PIPE).communicate()[0]
    return mime_data.decode("utf-8")

def is_ascii_file(filename):
    """
    Returns True if the given file is an ASCII file, False otherwise.
    """
    file_cmd_path = os.path.join(os.sep, 'usr', 'bin', 'file')
    if os.path.exists(file_cmd_path) and os.access(file_cmd_path, os.X_OK):
        file_cmd = ' '.join([file_cmd_path, '--brief', filename])
        file_output = subprocess.Popen(file_cmd, shell=True,
                                       stdout=subprocess.PIPE).stdout
        file_type = file_output.read().decode("utf-8").strip()
        if file_type.find('ASCII') != -1:
            return True
        else:
            return False
    else:
        err_msg = 'Error!  Unable to run the file command.'
        sys.exit(err_msg)

def is_hdf4(mime_data):
    """
    Return True when the mime data is from netCDF4/HDF 5 file.
    """
    return re.search('Hierarchical.*version.4', mime_data)

def is_netcdf4(mime_data):
    """
    Return True when the mime data is from netCDF4/HDF 5 file.
    """
    return re.search('Hierarchical.*version.5', mime_data)

def is_tar_file(file_path):
    """
    This function is deprecated.  Using it is discouraged.  Please call
    tarfile.is_tarfile directly.

    Returns a boolean telling if the file is a tar archive file.
    """
    # is_tar = False
    # try:
    #     test_tar_obj = tarfile.TarFile(file_path)
    #     is_tar = True
    #     test_tar_obj.close()
    # except:
    #     pass
    return tarfile.is_tarfile(file_path)

def dump_metadata(filename):
    """Dump file metadata:
        Call functions to get HDF 4 and HDF 5 header data
        read ASCII header from MERIS N1 files
    """

    # does input file exist?
    if not os.path.isfile(filename):
        print("Can't find input file '" + filename + "'.")
        return None

    lib3_bin_dir = os.getenv('LIB3_BIN')
    if not lib3_bin_dir:
        sys.exit('Error! Unable to locate LIB3_BIN environment variable. You may need to run')
    ncdump = os.path.join(lib3_bin_dir, 'ncdump')
    ncdump_hdf = os.path.join(lib3_bin_dir, 'ncdump_hdf')

    # mimecmd = ['file', '--brief', filename]
    # mime = subprocess.Popen(mimecmd, stdout=subprocess.PIPE).communicate()[0]
    mime = get_mime_data(filename)

    if mime.strip() == 'data':
        content = get_hdf5_header_xml(filename)
        if content:
            return content

    if re.search('Hierarchical.*version.4', mime):
        contents = get_hdf4_content(filename)
        return contents
    elif re.search('Hierarchical.*version.5', mime):
        content = get_hdf5_header_xml(filename)
        return content
    elif re.search('NetCDF Data Format', mime):
        if not (os.path.isfile(ncdump_hdf) and os.access(ncdump_hdf, os.X_OK)):
            print(ncdump_hdf, "is not executable.")
            return None
        cmd = ' '.join([ncdump_hdf, '-h', filename])
        hdr_content = subprocess.Popen(cmd, shell=True,
                                       stdout=subprocess.PIPE).communicate()
        return hdr_content[0].decode("utf-8").split('\n')
    else:
        fbuffer = open(filename, 'r', 1)
        try:
            line1 = fbuffer.readline()
            fbuffer.close()
    
            if re.search("HDF_UserBlock", line1):
                content = get_hdf5_header_xml(filename)
                return content
            elif line1[0:3] == 'CDF':
                # For NetCDF files, such as some from MERIS
                cmd = [ncdump, '-h', filename]
                hdr_content = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
                return hdr_content.read().decode("utf-8")
            else:
                header = []
                fbuffer = open(filename, 'r', 100)
                #for line in fbuffer.readlines(100):
                line = fbuffer.readline()
                while line:
                    line = line.strip()
                    if len(line):
                        header.append(line)
                        if re.search('LAST_LAST_LONG', line):
                            break
                    line = fbuffer.readline()
                fbuffer.close()
                return header
        except UnicodeDecodeError:
            return []

def readMetadata(filename):
    """
    Returns a dictionary containing the metadata for the file named by filename.
    """
    # todo: MERIS N1 files?
    text = dump_metadata(filename)
    # Added text == [] & changed exit() to sys.exit()    -Matt, Feb. 15, 2012
    # Kept an exit here (instead of making it a return) as already
    # existing programs assume the output from this function is good.
    if text is None or text == '':
        sys.exit("Error!  dump_metadata failed.")

    attrs = None

    # extract meaningful parts
    if isinstance(text, list):
        if text == []:
            return attrs
        elif re.search('PRODUCT', text[0]):
            attrs = {}
            for line in text:
                (key, value) = str(line).split('=')
                attrs[key] = str(value).strip('"')
            return attrs
        elif text[0][0:4] == 'CWIF':
            return {'Title': 'SeaWiFS Level-0'}
        elif text[0].find('GROUP = L1_METADATA_FILE') != -1:
            in_metadata_group = False
            attrs = {}
            for line in text:
                if in_metadata_group:
                    if line.find('END_GROUP = PRODUCT_METADATA') != -1:
                        break
                    else:
                        line_parts = line.split('=')
                        attr_key = line_parts[0].strip()
                        attr_val = line_parts[1].strip()
                        attrs[attr_key] = attr_val
                elif line.find('GROUP = PRODUCT_METADATA') != -1:
                    in_metadata_group = True
        else:
            for line in text:
                if line.find('title = ') != -1:
                    if line.find('Daily-OI') != -1:
                        # NOAA supplied SST Ancillary files
                        return {'Title': 'Ancillary', 'Data Type': 'SST'}
    elif isinstance(text, bytes) and (text[0:6] == 'netcdf'):
        attrs = {}
        lines = text.split('\n')
        for line in lines:
            if line.find('=') != -1:
                fields = line.split('=')
                key = fields[0]
                pos = 0
                while (not fields[0][pos].isalpha()) and pos < len(fields[0]):
                    key = key[1:]
                    pos += 1
                attrs[key.strip()] = fields[1].strip()
        return attrs
    elif isinstance(text, bytes) and (text[0:4] == 'HDF5'):
        attrs = get_hdf5_attr(text)
        return attrs
    # elif isinstance(text, types.StringType) and text[0:4] == 'HDF5':
    #     attrs = get_hdf5_attr(text)
    elif re.search(r'<\?xml', text)  or (text[0:4] == 'HDF5'):
        # if hdf5 file
        attrs = get_xml_attr(text)
    else:
        #if hdf4 file
        file_attr_re = re.compile('File attributes:(.+?)\n',
                                  re.MULTILINE | re.DOTALL)
        file_attr_results = file_attr_re.search(text)
        if file_attr_results != None:
            file_attr_var_re = re.compile('File attributes:(.+?)\nVariable',
                                          re.MULTILINE | re.DOTALL)
            file_attr_var_results = file_attr_var_re.search(text)
            if file_attr_var_results != None:
                allmeta = file_attr_var_results.group(1)
                # remove spaces around "=" to speed future searches
                allmeta = re.sub(r'\s*=\s*', '=', allmeta)
                # parse each file attribute
                attrs = get_odl_attr(allmeta)
            else:
                attrs = \
                get_attr(text)
    return attrs

def get_attr(text):
    """
    :param text: Text containing metadata to be parsed.
    :return: A dictionary containing metadata attributes.
    """
    attrs = {}
    lines = text.split('\n')
    attr_pattern = re.compile(r'^\s*Attr\d+: Name = ')
    value_pattern = re.compile(r'^\s*Value = ')
    in_attr = False
    for line in lines:
        if re.match(attr_pattern, line):
            in_attr = True
            attr_name = line.split('=')[1].strip()
        elif in_attr:
            if re.match(value_pattern, line):
                val = str(line).split('=', 1)[1].strip()
                if attr_name == 'Input Parameters':
                    attrs[attr_name] = {}
                    params = val.split('|')
                    for param in params:
                        parts = param.split('=')
                        if len(parts) == 2:
                            attrs[attr_name][parts[0].strip()] = parts[1].strip()
                else:
                    attrs[attr_name] = val
    return attrs

def get_hdf5_attr(header_text):
    """ Returns a Python dictionary containing the file metadata passed from
    header_text. The dictionary keys will the attribute names and the values
    will be the data values for the attributes. """
    attributes = {}
    attr_regex = re.compile(r'ATTRIBUTE "')
    data_item_regex = re.compile(r'\(\d+(,\d+)?\): ".+"')
    data_open_regex = re.compile(r'DATA \{')
    close_regex = re.compile(r' \}')
    data_lines = header_text.split('\n')
    in_attr = False
    in_data = False
    for line in data_lines:
        if attr_regex.search(line):
            in_attr = True
            attr_name = re.search(r'ATTRIBUTE "(.+)"', line).group(1)
            attributes[attr_name] = ''
        elif data_open_regex.search(line):
            in_data = True
        elif in_data:
            if close_regex.search(line):
                in_data = False
            # elif data_item_regex.search(line):
            elif re.search(r'\(\d+\)\:', line):
                # data_name = re.search(r'\(\d+(,\d+)?\): "(.+)"', line).group(2)
                # Because the data fields can start or end with extra spaces
                # both inside and outside the quotation marks, there are
                # multiple calls to .strip().
                the_data = line.split(':')[1].strip().strip('"').strip()
                attributes[attr_name] = the_data
        elif in_attr and close_regex.search(line):
            in_attr = False
    return attributes

def get_odl_attr(metatext):
    """
    get interesting bits from ODL formatted metadata
    """
    attrs = {}
    pattern = r'^\s*Attr\d+: Name=(.+?)\s*Type=(.+?)\s*Count=(.+?)\s*Value=(.+?)$'
    re_attr = re.compile(pattern, re.MULTILINE | re.DOTALL)

    for att in re_attr.finditer(metatext):
        name, dtype, count, value = att.groups()

        if 'char' in dtype:
            # interpret ASCII codes
            value = re.sub(r'\\000', '', value)   # null
            value = re.sub(r'\\011', '\t', value) # horizontal tab
            value = re.sub(r'\\012', '\n', value) # newline

        else:
            # add commas between array elements so they'll evaluate correctly
            if eval(count) > 1:
                value = ','.join(value.split())
                # evaluate string to numerical type
            value = set_type(value)

        if 'Metadata.' in name:
            # interpret ODL heirarchy
            value = parse_odl(value)

        # add attribute to dictionary
        attrs[name] = value

    # eliminate redundant info, then return dictionary.
    prune_odl(attrs)
    return attrs

def add_xml_group(group, attr):
    """
    add xml attributes to attr and decend groups
    """
    for node in group:
        if node.tag == 'Attribute':
            try:
                key = node.attrib['Name']
                val = node.find('Data').find('DataFromFile').text.strip().strip('"')
                attr[key] = val
            except:
                pass
        elif node.tag == 'Group' or node.tag == 'Dataset':
            add_xml_group(node, attr)


def get_xml_attr(metaxml):
    """
    parse xml formatted metadata
    """
    import xml.etree.ElementTree as ET

    attr = {}
    root = ET.fromstring(metaxml).find('RootGroup')
    add_xml_group(root, attr)
    return attr


def parse_odl(text):
    """Recursively extract ODL groups and objects."""

    # descend into GROUP/OBJECT heirarchy
    pattern = r"(GROUP|OBJECT)=(.+?)$(.+?)END_\1=\2"
    re_odl = re.compile(pattern, re.MULTILINE | re.DOTALL)
    items = {}
    blocks = re_odl.findall(text)
    for block in blocks:
        key = block[1]
        value = block[2]
        items[key] = parse_odl(value)

    # get value(s) at innermost level
    if not len(list(items.keys())):
        for line in text.splitlines():
            get_value(line, items)

    return items

def get_value(text, items=None):
    """Interpret text as key/value pairs, if possible."""
    if items is None:
        items = {}
    try:
        key, value = [i.strip() for i in text.split('=', 1)]
        items[key] = set_type(value)
    except ValueError:
        pass
    return items


def set_type(value):
    """Parse string value into correct type"""
    try:
        return eval(value)
    except (NameError, SyntaxError, TypeError):
        return value  # leave unchanged anything that can't be evaluated


def prune_odl(metadict):
    du.delete_key(metadict, 'StructMetadata.[0-9]')
    du.delete_key(metadict, '(NUM_VAL|CLASS)')
    du.promote_value(metadict, '.*VALUE')
    du.reassign_keys_in_dict(metadict,
                             'ADDITIONALATTRIBUTENAME', 'INFORMATIONCONTENT')
    du.flatten_dict(metadict)
    return
