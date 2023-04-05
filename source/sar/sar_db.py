
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
    """ Correct some "not allowed" names in mysql"""
    name = name.replace('-','_')
    name = name.replace('system', 'system_')

    return(name)


