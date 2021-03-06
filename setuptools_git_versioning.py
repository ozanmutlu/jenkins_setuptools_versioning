#!/usr/bin/python

# -*- coding: utf-8 -*-

import os
import re
import subprocess
from datetime import datetime
from distutils.errors import DistutilsSetupError
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Union

from setuptools.dist import Distribution

if TYPE_CHECKING:
    from re import Pattern

DEFAULT_TEMPLATE = "{tag}"  # type: str
DEFAULT_DEV_TEMPLATE = "{tag}.dev{ccount}+{sha}"  # type: str
DEFAULT_DIRTY_TEMPLATE = "{tag}.dev{ccount}+{sha}.dirty"  # type: str
DEFAULT_STARTING_VERSION = "0.0.1"
ENV_VARS_REGEXP = re.compile(r"\{env:([^:}]+):?([^}]+}?)?\}", re.IGNORECASE | re.UNICODE)  # type: Pattern
TIMESTAMP_REGEXP = re.compile(r"\{timestamp:?([^:}]+)?\}", re.IGNORECASE | re.UNICODE)  # type: Pattern


def _exec(cmd):  # type: (str) -> List[str]
    try:
        stdout = subprocess.check_output(cmd, shell=True, universal_newlines=True)  # nosec
    except subprocess.CalledProcessError as err:
        stdout = err.output
    lines = stdout.splitlines()
    return [line.rstrip() for line in lines if line.rstrip()]


def get_branch():  # type: () -> Optional[str]
    branch_name = os.environ.get("BRANCH_NAME")
    if branch_name:
        return branch_name
    branches = _exec("git rev-parse --abbrev-ref HEAD")
    if branches:
        return branches[0]
    return None


def get_all_tags(sort_by="version:refname"):  # type: (str) -> List[str]
    tags = _exec("git tag --sort=-{}".format(sort_by))
    if tags:
        return tags
    return []


def get_branch_tags(sort_by="v:refname"):  # type: (str) -> List[str]
    tags = _exec("git tag --sort=-{}".format(sort_by))
    if tags:
        return tags
    return []


def get_tag(*args, **kwargs):  # type: (*str, **str) -> Optional[str]
    #tags = get_branch_tags(*args, **kwargs)
    tags = get_latest_tag_on_branch()
    if tags:
        return tags[0]
    return None

def get_latest_tag_on_branch():
    latest_tag_on_branch = _exec("git describe --tags --abbrev=0")
    if latest_tag_on_branch:
        return latest_tag_on_branch
    return []


def next_tag_version(current_tag):
    current_branch = get_branch()
    current_tag = current_tag.lstrip("v")
    current_tag_list = current_tag.split(".")

    if len(current_tag_list) == 2:
        current_tag_list.append("0")
    elif len(current_tag_list) > 3 or len(current_tag_list) < 2:
        raise Exception("Check the tags, example tag: v2.3.1")

    if "feature/" in current_branch or current_branch == "develop":
        minor_increased = int(current_tag_list[1]) + 1
        return str("v{}.{}.0".format(current_tag_list[0], minor_increased))
    else:
        patch_increased = int(current_tag_list[2]) + 1
        return str("v{}.{}.{}".format(current_tag_list[0], current_tag_list[1], patch_increased))


def get_sha(name="HEAD"):  # type: (str) -> Optional[str]
    sha = _exec('git rev-list -n 1 "{}"'.format(name))
    if sha:
        return sha[0]
    return None


def get_latest_file_commit(path):  # type: (str) -> Optional[str]
    sha = _exec('git log -n 1 --pretty=format:%H -- "{}"'.format(path))
    if sha:
        return sha[0]
    return None


def is_dirty():  # type: () -> bool
    res = _exec("git status --porcelain --untracked-files=no :!setup.cfg")
    if res:
        return True
    return False


def count_since(name):  # type: (str) -> Optional[int]
    res = _exec('git rev-list --count HEAD "^{}"'.format(name))
    if res:
        return int(res[0])
    return None


def parse_config(dist, _, value):  # type: (Distribution, Any, Any) -> None
    if isinstance(value, bool):
        if value:
            version = version_from_git()
            dist.metadata.version = version
            return
        else:
            raise DistutilsSetupError("Can't be False")

    template = value.get("template", DEFAULT_TEMPLATE)
    dev_template = value.get("dev_template", DEFAULT_DEV_TEMPLATE)
    dirty_template = value.get("dirty_template", DEFAULT_DIRTY_TEMPLATE)
    starting_version = value.get("starting_version", DEFAULT_STARTING_VERSION)
    version_callback = value.get("version_callback", None)
    version_file = value.get("version_file", None)
    count_commits_from_version_file = value.get("count_commits_from_version_file", False)
    branch_formatter = value.get("branch_formatter", None)
    sort_by = value.get("sort_by", None)

    version = version_from_git(
        template=template,
        dev_template=dev_template,
        dirty_template=dirty_template,
        starting_version=starting_version,
        version_callback=version_callback,
        version_file=version_file,
        count_commits_from_version_file=count_commits_from_version_file,
        branch_formatter=branch_formatter,
        sort_by=sort_by,
    )
    dist.metadata.version = version


def read_version_from_file(path):  # type: (Union[str, os.PathLike]) -> str
    with open(path) as file:
        return file.read().strip()


def subst_env_variables(template):  # type: (str) -> str
    if "{env" in template:
        for var, default in ENV_VARS_REGEXP.findall(template):
            if default.upper() == "IGNORE":
                default = ""
            elif not default:
                default = "UNKNOWN"

            value = os.environ.get(var, default)
            template, _ = ENV_VARS_REGEXP.subn(value, template, count=1)

    return template


def subst_timestamp(template):  # type: (str) -> str
    if "{timestamp" in template:
        now = datetime.now()
        for fmt in TIMESTAMP_REGEXP.findall(template):
            result = now.strftime(fmt or "%s")
            template, _ = TIMESTAMP_REGEXP.subn(result, template, count=1)

    return template


def version_from_git(
    template=DEFAULT_TEMPLATE,  # type: str
    dev_template=DEFAULT_DEV_TEMPLATE,  # type: str
    dirty_template=DEFAULT_DIRTY_TEMPLATE,  # type: str
    starting_version=DEFAULT_STARTING_VERSION,  # type: str
    version_callback=None,  # type: Union[Any, Callable, None]
    version_file=None,  # type: Optional[str]
    count_commits_from_version_file=False,  # type: bool
    branch_formatter=None,  # type: Optional[Callable[[str], str]]
    sort_by=None,  # type: Optional[str]
):
    # type: (...) -> str
    
    # Check if PKG-INFO exists and return value in that if it does
    if os.path.exists("PKG-INFO"):
        with open("PKG-INFO") as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("Version:"):
                return line[8:].strip()

    from_file = False
    tag = get_tag(sort_by) if sort_by else get_tag()
    if tag is None:
        if version_callback is not None:
            if callable(version_callback):
                return version_callback()
            else:
                return version_callback

        if version_file is None or not os.path.exists(version_file):
            return starting_version
        else:
            from_file = True
            tag = read_version_from_file(version_file)

            if not count_commits_from_version_file:
                return tag.lstrip("v")  # for tag "v1.0.0" drop leading "v" symbol

            tag_sha = get_latest_file_commit(version_file)
    else:
        tag_sha = get_sha(tag)
        next_tag = next_tag_version(tag)

    dirty = is_dirty()
    head_sha = get_sha()
    full_sha = head_sha if head_sha is not None else ""
    ccount = count_since(tag_sha) if tag_sha is not None else None
    on_tag = head_sha is not None and head_sha == tag_sha and not from_file

    branch = get_branch()
    if branch_formatter is not None and branch is not None:
        branch = branch_formatter(branch)

    if dirty:
        t = dirty_template
    elif not on_tag and ccount is not None:
        t = dev_template
    else:
        t = template

    t = subst_env_variables(t)
    t = subst_timestamp(t)

    if t is template:
        version = t.format(sha=full_sha[:8], tag=tag, ccount=ccount, branch=branch, full_sha=full_sha)
    else:
        version = t.format(sha=full_sha[:8], tag=next_tag, ccount=ccount, branch=branch, full_sha=full_sha)

    # Ensure local version label only contains permitted characters
    public, sep, local = version.partition("+")
    local_sanitized = re.sub(r"[^a-zA-Z0-9.]", ".", local)
    public_sanitized = public.lstrip("v")  # for version "v1.0.0" drop leading "v" symbol
    return public_sanitized + sep + local_sanitized