import configparser
import os
import glob

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")
DEFAULT_CONFIG = """[Settings]
collections_dir =
covers_dir =

[API Keys]
omdb = ebed58dc
tmdb =
"""


def ensure_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            f.write(DEFAULT_CONFIG)


def get_collections_dir():
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if config.has_section("Settings") and config.has_option("Settings", "collections_dir"):
        return config.get("Settings", "collections_dir").strip()
    return ""


def set_collections_dir(path):
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if not config.has_section("Settings"):
        config.add_section("Settings")
    config.set("Settings", "collections_dir", path)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)


def get_covers_dir():
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if config.has_section("Settings") and config.has_option("Settings", "covers_dir"):
        path = config.get("Settings", "covers_dir").strip()
        if path and not os.path.isabs(path):
            path = os.path.join(os.path.dirname(CONFIG_PATH), path)
        return path
    return ""


def set_covers_dir(path):
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if not config.has_section("Settings"):
        config.add_section("Settings")
    config.set("Settings", "covers_dir", path)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)


def scan_collection_files():
    col_dir = get_collections_dir()
    if not col_dir or not os.path.isdir(col_dir):
        return {}
    pattern = os.path.join(col_dir, "collections_*.json")
    files = sorted(glob.glob(pattern))
    result = {}
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        result[name] = fp
    return result


def get_api_key(service):
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if config.has_section("API Keys") and config.has_option("API Keys", service):
        return config.get("API Keys", service).strip()
    return ""


def get_channel_names():
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if config.has_section("Channels"):
        items = config.items("Channels")
        if items:
            return dict(items)
    project_root = os.path.dirname(CONFIG_PATH)
    pattern = os.path.join(project_root, "*.json")
    json_files = sorted(glob.glob(pattern))
    result = {}
    for fp in json_files:
        stem = os.path.splitext(os.path.basename(fp))[0]
        if stem != "config":
            result[stem] = stem
    return result


def set_channel_names(channels):
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if config.has_section("Channels"):
        config.remove_section("Channels")
    config.add_section("Channels")
    for key, val in channels.items():
        config.set("Channels", key, val)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)


def set_api_key(service, key):
    ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    if not config.has_section("API Keys"):
        config.add_section("API Keys")
    config.set("API Keys", service, key)
    with open(CONFIG_PATH, "w") as f:
        config.write(f)
