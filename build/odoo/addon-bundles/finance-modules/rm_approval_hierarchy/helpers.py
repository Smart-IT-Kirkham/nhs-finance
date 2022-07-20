def get_rm_fields_to_be_tracked():
    """A process that will be updated manually in case there
    are added or removed other fields. Actually are added all fields that are
    visible in gui on the respective models"""
    return {
        "hr.job": [
            "group_id",
        ],
    }
