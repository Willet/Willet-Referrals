#!/usr/bin/env python

# template library to allow loading templates from multiple root folders
# hacked from:
# http://groups.google.com/group/google-appengine/browse_thread/thread/c3e0e4c47e4f3680/262b517a723454b6?lnk=gst&q=template_dirs#262b517a723454b6
import os

from google.appengine.ext.webapp.template import Context
from google.appengine.ext.webapp.template import _swap_settings
from google.appengine.ext.webapp.template import _urlnode_render_replacement
from google.appengine.ext import webapp
webapp._config_handle.django_setup()

import django

from util.consts import TEMPLATE_DIRS 

def render(template_path, template_dict, use_consts=True, debug=False, template_dirs=()): 
    """Renders the template at the given path with the given dict of 
    values. 
    Example usage: 
        render("templates/index.html", {"name": "Bret", "values": [1, 2, 3]}) 
    Args: 
        template_path: path to a Django template 
        template_dict: dictionary of values to apply to the template 
    """ 
    if use_consts:
        template_dirs += TEMPLATE_DIRS

    t = load(template_path, debug, template_dirs) 
    return t.render(Context(template_dict)) 

template_cache = {} 

def load(path, debug=False, template_dirs=()): 
    """Loads the Django template from the given path. 
    It is better to use this function than to construct a Template using the 
    class below because Django requires you to load the template with a 
    method if you want imports and extends to work in the template. 
    """ 

    abspath = os.path.abspath(path) 
    if not debug: 
        template = template_cache.get(abspath, None) 
    else: 
        template = None 

    if not template: 
        directory, file_name = os.path.split(abspath) 
        new_settings = { 
            'TEMPLATE_DIRS': (directory,) + template_dirs, 
            'TEMPLATE_DEBUG': debug, 
            'DEBUG': debug, 
        } 
        old_settings = _swap_settings(new_settings) 
        try: 
            template = django.template.loader.get_template(file_name) 
        finally: 
            _swap_settings(old_settings) 
        if not debug: 
            template_cache[abspath] = template 

        def wrap_render(context, orig_render=template.render): 
            URLNode = django.template.defaulttags.URLNode 
            save_urlnode_render = URLNode.render 
            old_settings = _swap_settings(new_settings) 
            try: 
                URLNode.render = _urlnode_render_replacement 
                return orig_render(context) 
            finally: 
                _swap_settings(old_settings) 
                URLNode.render = save_urlnode_render 
        template.render = wrap_render 
    return template

