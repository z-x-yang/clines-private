# Function to get all unique tags from list1
def get_tags_from_list1(list1):
    return {int(item['TAG']) for item in list1}

# Remove items with tags not in list1 and ensure all tags in list1 are in list2 and list3


def clean_and_fill_list(main_tags, lst, tag_key, default_item):
    # Remove items with tags not in list1
    cleaned_list = {int(item[tag_key]): item for item in lst if int(
        item[tag_key]) in main_tags}

    # Fill missing tags with default items
    for tag in main_tags:
        if tag not in cleaned_list:
            new_item = default_item.copy()
            new_item[tag_key] = tag
            cleaned_list[tag] = new_item

    # Return list ordered by the tags in list1
    return [cleaned_list[tag] for tag in main_tags]

# Main processing function


def process_lists_based_on_list1(list1, list2, list3, list4, list5):
    # Get all unique tags from list1
    main_tags = get_tags_from_list1(list1)

    # Clean and fill list2 based on tags from list1
    list2_cleaned = clean_and_fill_list(main_tags, list2, 'tag', {
        "tag": None,
        "body_location": None,
        "value": None,
        "unit": None,
        "infer": None,
        "note": None,
        "freq": None,
        "route": None,
        "other": None,
    })

    list3_cleaned = clean_and_fill_list(main_tags, list3, 'tag', {
        "tag": None,
        "assertion_status": None,
    })
    for idx, item in enumerate(list3_cleaned):
        if item["assertion_status"] == "Not associated":
            list3_cleaned[idx]["assertion_status"] = "Notassociated"

    # Clean and fill list3 based on tags from list1
    list4_cleaned = clean_and_fill_list(main_tags, list4, 'tag', {
        "tag": None,
        "date": [None, None],
        "inferred": [None, None]
    })

    list5_cleaned = clean_and_fill_list(main_tags, list5, 'tag', {
        "tag": None,
        "related": {}  # Changed from list to dictionary
    })

    return list2_cleaned, list3_cleaned, list4_cleaned, list5_cleaned
