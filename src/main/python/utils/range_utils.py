def remap(value, old_min, old_max, new_min, new_max):
    normalized_old_value = (value - old_min) / (old_max - old_min)  # Between 0 and 1
    new_offset = normalized_old_value * (new_max - new_min)
    return new_min + new_offset
