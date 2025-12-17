# ...existing code...
#!/usr/bin/env python3
"""Replace full https links in HTML files using mappings from convert.json."""
from pathlib import Path
import json
import re
import urllib.request
import urllib.parse
import os
import requests

# env setup
original_files_folder = "original files"
all_routes_file="all_routes.json"

images_folder = "src/images"

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


def download_images(all_routes_file=all_routes_file, images_folder=images_folder, debug=0, count = -1):
    root = get_root_path()
    images_dir = root / images_folder
    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(root / all_routes_file, "r", encoding="utf-8") as infile:
            all_routes = json.load(infile)
    except FileNotFoundError:
        if debug:
            print("all routes file not found:", root / all_routes_file)
        return [], [(None, "all_routes_file not found")]
    img_routes = [r for r in all_routes if r.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
    # print(len(img_routes), img_routes[0])
    
    counter = 0
    for img in img_routes:
        if img[-1] == "/":
            img = img[:-1]
        base_name = img.split("/")[-1]
        base_file_path = images_dir / base_name

        if base_file_path.exists():
            continue
        else:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible)"}
                resp = requests.get(img, headers=headers, stream=True, timeout=15, allow_redirects=True)
                response = requests.get(img)
                if response.status_code == 200:
                                        
                    with open(base_file_path, "wb") as out:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                out.write(chunk)
                    if debug:
                        print("downloaded image:", base_name)
                else:
                    if debug:
                        print("failed to download (status):", resp.status_code, img)
            except Exception as e:
                if debug:
                    print("error downloading image:", img, " error:", e)
        counter += 1
        if counter != -1 and counter >= count:
            break


    

# delete_html_files()
# copy_original_files()
# change_html_file_names()

# get_all_routes(save=1)

download_images(debug=1)