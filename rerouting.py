# ...existing code...
#!/usr/bin/env python3
"""Replace full https links in HTML files using mappings from convert.json."""
from pathlib import Path
import json
import re

# env setup
original_files_folder = "original files"
all_routes_file="all_routes.json"

# utility functions 
def get_root_path():
    return Path(__file__).parent

# functions
def delete_html_files(debug=0):
    root = get_root_path()
    html_files = list(root.glob("*.html"))
    for f in html_files:
        if debug:
            print("deleting: ", f)
        f.unlink()

def copy_original_files(_original_files_folder=original_files_folder, debug=0):
    root = get_root_path()
    original_folder = root / _original_files_folder
    html_files = list(original_folder.glob("*.html"))
    for f in html_files:
        destination = root / f.name
        if debug:
            print("copying: ", f, " to ", destination)
        content = f.read_text(encoding="utf-8")
        destination.write_text(content, encoding="utf-8")

def standardized_name(name):
    new_name = name.replace(" - Explore & Capture", "").lower()
    idx = new_name.find("_")
    if idx != -1:
        new_name = new_name[:idx]
    new_name = new_name.replace(" ", "-")
    return new_name

def change_html_file_names(debug=0):
    root = get_root_path()
    html_files = list(root.glob("*.html"))
    for f in html_files:
        new_name = standardized_name(f.stem)

        new_path = root / f"{new_name}.html"
        if debug:
            print("renaming: ", f, " to ", new_path)
        f.rename(new_path)

def get_all_routes(save=0, output_file=all_routes_file):
    all_routes = set()
    root = get_root_path()
    html_files = list(root.glob("*.html"))
    for f in html_files:
        read_content = f.read_text(encoding="utf-8")
        links = re.findall(r'https://[^\s"\'<>]+', read_content)
        all_routes.update(links)
    if save:
        with open(root / output_file, "w", encoding="utf-8") as outfile:
            json.dump(list(all_routes), outfile, indent=4)
    return all_routes

def get_img_from_all_routes(all_routes_file=all_routes_file):
    root = get_root_path()
    with open(root / all_routes_file, "r", encoding="utf-8") as infile:
        all_routes = json.load(infile)
    img_routes = [route for route in all_routes if route.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]

    print(len(img_routes))
    return img_routes

# delete_html_files()
# copy_original_files()
# change_html_file_names()

# get_all_routes(save=1)

get_img_from_all_routes()