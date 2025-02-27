#!/usr/bin/python3
# coding=utf-8

#   Copyright 2021 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Module """

from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import module  # pylint: disable=E0611,E0401

from .tools.repo import RepoResolver


class Module(module.ModuleModel):
    """ Pylon module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor
        #
        self.repo_resolver = None

    def init(self):  # pylint: disable=R0914
        """ Init module """
        log.info("Initializing module")
        #
        resolvers = []
        #
        for key in ["local_plugin_repo", "customer_plugin_repo", "plugin_repo"]:
            if key in self.descriptor.config:
                resolvers.append(self.descriptor.config[key])
        #
        self.repo_resolver = RepoResolver(self, resolvers)
        self.repo_resolver.init()
        #
        plugins_to_check = [
            *self.descriptor.config.get("local_preordered_plugins", []),
            *self.descriptor.config.get("customer_preordered_plugins", []),
            *self.descriptor.config.get("preordered_plugins", [])
        ]
        #
        known_plugins = set(plugins_to_check)
        plugins_provider = self.context.module_manager.providers["plugins"]
        #
        while plugins_to_check:
            plugin = plugins_to_check.pop(0)
            log.info("Preloading plugin: %s", plugin)
            #
            if plugins_provider.plugin_exists(plugin):
                log.info("Plugin %s already exists", plugin)
                #
                metadata = plugins_provider.get_plugin_metadata(plugin)
            else:
                plugin_info = self.repo_resolver.resolve(plugin)
                if plugin_info is None:
                    log.error("Plugin %s is not known", plugin)
                    continue
                #
                metadata_provider = self.repo_resolver.get_metadata_provider(plugin)
                #
                metadata_url = plugin_info["objects"]["metadata"]
                metadata = metadata_provider.get_metadata({"source": metadata_url})
                #
                source_target = plugin_info["source"].copy()
                source_type = source_target.pop("type")
                #
                if source_type != "git":
                    log.error("Plugin %s source type %s is not supported", plugin, source_type)
                    continue
                #
                source_provider = self.repo_resolver.get_source_provider(plugin)
                #
                source = source_provider.get_source(source_target)
                plugins_provider.add_plugin(plugin, source)
            #
            for dependency in metadata.get("depends_on", list()):
                if dependency in known_plugins:
                    continue
                #
                known_plugins.add(dependency)
                plugins_to_check.append(dependency)

    def deinit(self):  # pylint: disable=R0201
        """ De-init module """
        log.info("De-initializing module")
        #
        if self.repo_resolver is not None:
            self.repo_resolver.deinit()
