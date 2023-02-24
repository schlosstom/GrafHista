

def get_date_time(data_set):
    """ Returns date and time from the given index and combine it together"""
    path = data_set['timestamp']
    date_time = path['date'] + " " + path['time']
    return (date_time)


def data_type(value):
    """ Returns mysql value type based on the value type we get from the dict."""
    if isinstance(value, float):
        return(" FLOAT(32,2)")
    elif isinstance(value, str):
        return(" VARCHAR(255)")
    elif isinstance(value, int):
        return(" BIGINT")


def name_correction(name):
    """ Correct some not allowed names"""
    if '-' in name:
        name = name.replace('-','_')

    if name == 'system':
            name += '_'

    return(name)


def get_data_and_path(data_set):
    """ Returns the "key address and the name from the given index  """

    key_name = (set(data_set.keys()) - {'timestamp'}).pop()

    # Some data like cpu_load are stored in a single list element
    # We check for list and assume that there is only one list element [0].
    if isinstance(data_set[key_name], dict):
        value = data_set[key_name]
    elif isinstance(data_set[key_name], list):
        value = data_set[key_name][0]
    else:
        logging.error('get_data_and_path() - An error occures. Exit')
        sys.exit(1)

    # Unfortunately swap and memory have the same key_name "memory"
    # If there is a data key swapfree we will remane the key_name to "swap"
    if 'swpfree'  in value.keys():
        key_name = "swap"

    return  name_correction(key_name), value


def create_table_string(data_set):
    """ Returns the sql string for creating the table based on the given index """
    name, path = get_data_and_path(data_set)

    sql_string = "CREATE TABLE " + name + " (Date DATETIME"

    for key, value in path.items():
        key = name_correction(key)
        sql_string += ", " + key + data_type(value)

    sql_string += ")"

########    logging.info(f'create_table_string() - Creating table {sql_string}')
    return(sql_string)


def create_insert_string(data_set):
    """ Returns the sql string for inserting proper data to the table based on the given index """
    date = get_date_time(data_set)
    name, path = get_data_and_path(data_set) 

    sql_string = "INSERT INTO " + name + " SET Date = \'" + date  + "\'"

    for key, value in path.items():
        key = name_correction(key)
        sql_string += ", " + str(key) + " = \'" + str(value) + "\' "

    return(sql_string)


