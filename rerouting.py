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
from PIL import Image

# env setup
original_files_folder = "original files"
all_routes_file="all_routes.json"

images_folder = "src/images"

prev_base_html = "https://exploreandcapture.com"

# utility functions 
def get_root_path():
    return Path(__file__).parent

def local_image_info(path):
    p = Path(path)
    size_bytes = p.stat().st_size
    with Image.open(p) as im:
        width, height = im.size
    return size_bytes / (1024 ** 2), (width, height)

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

def standardized_html_name(name):
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
        new_name = standardized_html_name(f.stem)

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
    img_routes = [route for route in all_routes if route.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))]

    print(len(img_routes))
    return img_routes


def pick_largest_image_urls(urls):
    """Group image URLs by base filename (strip -{WxH} suffix) and pick the largest width.

    Returns a list of chosen URLs (one per base image).
    """
    groups = {}
    for u in urls:
        try:
            parsed = urllib.parse.urlparse(u)
            name = Path(urllib.parse.unquote(parsed.path)).name
        except Exception:
            continue
        # base filename without WP size suffix like -1024x768
        base = re.sub(r'-\d+x\d+(?=\.)', '', name)
        m = re.search(r'-(\d+)x(\d+)(?=\.)', name)
        w = int(m.group(1)) if m else 0
        cur = groups.get(base)
        if cur is None or w > cur[0]:
            groups[base] = (w, u)
    return [info[1] for info in groups.values()]

def download_images(all_routes_file=all_routes_file, images_folder=images_folder, debug=0, count = None):
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
    # reduce to only the largest variant per image base
    img_routes = pick_largest_image_urls(img_routes)
    # print(len(img_routes), img_routes[0])
    
    counter = 0
    for img in img_routes:
        if img.endswith('/'):
            img = img[:-1]
        try:
            parsed = urllib.parse.urlparse(img)
            base_name = Path(urllib.parse.unquote(parsed.path)).name
        except Exception:
            base_name = ''

        if not base_name:
            base_name = f"image_{counter}.jpg"

        # sanitize filename for filesystem
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', base_name)
        base_file_path = images_dir / safe_name

        if base_file_path.exists():
            if debug:
                print('exists:', base_file_path.name)
            counter += 1
            if count is not None and counter >= count:
                break
            continue

        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible)", "Accept": "image/*, */*"}
            resp = requests.get(img, headers=headers, stream=True, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                with open(base_file_path, "wb") as out:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            out.write(chunk)
                if debug:
                    size_mb, _ = local_image_info(base_file_path)
                    print("downloaded image:", base_file_path.name, f"{size_mb:.2f}", "MB")
            else:
                if debug:
                    print("failed to download (status):", resp.status_code, img)
        except Exception as e:
            if debug:
                print("error downloading image:", img, " error:", e)
        counter += 1
        if count is not None and counter >= count:
            break

def reroute_imgs_to_local(images_folder=images_folder, html_dir=None, debug=False):
    root = get_root_path()
    images_dir = root / images_folder

    img_re = re.compile(r'<img\b[^>]*>', re.I | re.S)
    src_re = re.compile(r'src\s*=\s*([\'"])(.*?)\1', re.I | re.S)
    srcset_re = re.compile(r'srcset\s*=\s*([\'"])(.*?)\1', re.I | re.S)
    width_re = re.compile(r'width\s*=\s*([\'\"])?\d+([\'\"])?', re.I)
    height_re = re.compile(r'height\s*=\s*([\'\"])?\d+([\'\"])?', re.I)

    modified = []
    for html in root.glob("*.html"):
        text = html.read_text(encoding="utf-8")
        new_text = text
        changed = False

        for tag in img_re.findall(text):
            src_m = src_re.search(tag)
            srcset_m = srcset_re.search(tag)

            # collect candidate URLs (src + all srcset urls)
            candidates = []
            if src_m and src_m.group(2).strip():
                candidates.append(src_m.group(2).strip())
            if srcset_m and srcset_m.group(2).strip():
                for part in re.split(r',\s*', srcset_m.group(2).strip()):
                    url = part.split()[0]
                    if url:
                        candidates.append(url)

            if not candidates:
                continue

            # try to find a local file: exact filename first, then base-name match
            chosen_name = None
            for url in candidates:
                name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
                if not name:
                    continue
                if (images_dir / name).exists():
                    chosen_name = name
                    break

            if not chosen_name:
                for url in candidates:
                    name = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
                    if not name:
                        continue
                    base = re.sub(r'-\d+x\d+(?=\.)', '', name)
                    for p in images_dir.iterdir():
                        if p.is_file() and p.name.startswith(base):
                            chosen_name = p.name
                            break
                    if chosen_name:
                        break

            if not chosen_name:
                continue

            local_path = f"{images_folder.replace('\\','/')}/{chosen_name}"

            # build new tag
            new_tag = tag
            if src_m:
                new_tag = src_re.sub(f'src="{local_path}"', new_tag, count=1)
            else:
                if new_tag.endswith('/>'):
                    new_tag = new_tag[:-2] + f' src="{local_path}" />'
                else:
                    new_tag = new_tag[:-1] + f' src="{local_path}">'

            if srcset_m:
                # try to pick a width descriptor from srcset (max w) for nicer srcset rewrite
                max_w = 0
                for part in re.split(r',\s*', srcset_m.group(2).strip()):
                    toks = part.split()
                    if len(toks) > 1 and toks[1].endswith('w'):
                        try:
                            w = int(toks[1][:-1])
                            if w > max_w:
                                max_w = w
                        except Exception:
                            pass
                replacement = f'srcset="{local_path} {max_w}w"' if max_w else f'srcset="{local_path}"'
                if srcset_re.search(new_tag):
                    new_tag = srcset_re.sub(replacement, new_tag, count=1)
                else:
                    if new_tag.endswith('/>'):
                        new_tag = new_tag[:-2] + ' ' + replacement + ' />'
                    else:
                        new_tag = new_tag[:-1] + ' ' + replacement + '>'

            # add/replace width and height attributes from the local image file
            try:
                img_file = images_dir / chosen_name
                with Image.open(img_file) as im:
                    w, h = im.size
                if width_re.search(new_tag):
                    new_tag = width_re.sub(f'width="{w}"', new_tag)
                if height_re.search(new_tag):
                    new_tag = height_re.sub(f'height="{h}"', new_tag)
                # if neither present, insert before the closing
                if not width_re.search(new_tag) and not height_re.search(new_tag):
                    if new_tag.endswith('/>'):
                        new_tag = new_tag[:-2].rstrip() + f' width="{w}" height="{h}" />'
                    else:
                        new_tag = new_tag[:-1].rstrip() + f' width="{w}" height="{h}">'
            except Exception:
                pass

            if new_tag != tag:
                new_text = new_text.replace(tag, new_tag, 1)
                changed = True

        if changed:
            html.write_text(new_text, encoding="utf-8")
            modified.append(html.name)
            if debug:
                print("rewrote images in", html.name)

    return modified

def reroute_links_to_local(html_dir=None, debug=False):
    root = get_root_path()

    link_re = re.compile(r'<a\b[^>]*href\s*=\s*([\'"])(.*?)\1', re.I | re.S)
        # handle <link href="..."> and <meta content="..."> tags
    aux_attr_re = re.compile(r'<(?:link|meta)\b[^>]*?(?:href|content)\s*=\s*([\'\"])(.*?)\1[^>]*>', re.I | re.S)

    modified = []
    for html in root.glob("*.html"):
        text = html.read_text(encoding="utf-8")
        new_text = text
        changed = False

        for match in link_re.finditer(text):
            full_url = match.group(2).strip()
            if full_url.startswith(prev_base_html):
                # strip query/fragment and normalize path
                parsed = urllib.parse.urlparse(full_url)
                path_part = parsed.path or '/'
                if not path_part.startswith('/'):
                    path_part = '/' + path_part

                candidate = root / path_part.lstrip('/')
                local_path = None

                # prefer a local .html file (e.g. /malaysia -> ./malaysia.html)
                if candidate.with_suffix('.html').exists():
                    local_path = f".{path_part.rstrip('/')}.html"
                # exact file exists (e.g. /somefile.html -> ./somefile.html)
                # elif candidate.exists() and candidate.is_file():
                #     local_path = f".{path_part}"

                if not local_path:
                    if debug:
                        print("skipping link (local target missing):", full_url, "->", candidate)
                    continue

                new_tag = match.group(0).replace(full_url, local_path, 1)
                new_text = new_text.replace(match.group(0), new_tag, 1)
                changed = True
            else:
                if debug:
                    print("skipping link (not matching base):", full_url)

            # also handle <link> and <meta> tags that point to the site root
            changed_aux = False
            for match in aux_attr_re.finditer(text):
                full_tag = match.group(0)
                # find the specific attribute (href or content) inside the tag
                attr_m = re.search(r'(href|content)\s*=\s*([\'\"])(.*?)\2', full_tag, re.I | re.S)
                if not attr_m:
                    continue
                full_url = attr_m.group(3).strip()
                if not full_url.startswith(prev_base_html):
                    continue

                parsed = urllib.parse.urlparse(full_url)
                path_part = parsed.path or '/'
                if not path_part.startswith('/'):
                    path_part = '/' + path_part

                candidate = root / path_part.lstrip('/')
                local_path = None

                if candidate.with_suffix('.html').exists():
                    local_path = f".{path_part.rstrip('/')}.html"
                elif candidate.exists() and candidate.is_file():
                    local_path = f".{path_part}"

                if not local_path:
                    if debug:
                        print("skipping auxiliary tag (local target missing):", full_url, "->", candidate)
                    continue

                new_tag = full_tag.replace(full_url, local_path, 1)
                new_text = new_text.replace(full_tag, new_tag, 1)
                changed_aux = True

            if changed_aux and html.name not in modified:
                # write once if not already written by the <a> pass
                html.write_text(new_text, encoding="utf-8")
                modified.append(html.name)
                if debug:
                    print(html, "rewrote auxiliary tags in", html.name)
        if changed:
            html.write_text(new_text, encoding="utf-8")
            modified.append(html.name)
            if debug:
                print(html, "rewrote links in", html.name)

    return modified


def main(debug=0):

    delete_html_files()
    copy_original_files()
    change_html_file_names()

    get_all_routes(save=1)

    download_images(debug=debug)
    reroute_imgs_to_local(debug=debug)
    reroute_links_to_local(debug=debug)

main(debug=0)

# root = get_root_path()
# html_files = list(root.glob("*.html"))
# print(len(html_files))

# for x in html_files:
#     print(x.name) # abc.html
#     print(x.stem) # abc
#     print(x.suffix) # .html