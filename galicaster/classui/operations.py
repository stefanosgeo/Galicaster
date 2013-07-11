# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/operations
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.
"""
UI for the operation manager
"""

import gtk
import pango
import gobject
from os import path

from elements.__init__ import Chooser
from selector import SelectorUI, MainList

from galicaster.operations import loader
from galicaster.core import context
from galicaster.classui import message

CREATE = 0
CLEAR = 1
EXECUTE = 2

class OperationsUI(SelectorUI):
    """
    Main window of the Operations Manager.
    It list the available operations, with tabs associated to configuration and confirmation.
    """
    
    __gtype_name__ = 'OperationsUI'

    def __init__(self, parent=None, size = None, mediapackage = None, UItype = 0):
        if not parent:
            parent = context.get_mainwindow()
        if not size:
            size = context.get_mainwindow().get_size()
        self.size = size

        title = ""
        if UItype == CREATE:
            title = "New Operations"
        elif UItype == CLEAR:
            title = "Clear Operations"
        elif UItype == EXECUTE:
            title = "Execute Operations"
        SelectorUI.__init__(self, parent, size, title)

        #configuration data
        self.mediapackage = mediapackage # TODO take into account single or multiple MPs
        tactile = context.get_conf().get('mediamanager', 'selection').lower() == "touch"
        self.list = OperationList(self, size, "Operation Information", UItype, tactile)
        self.add_main_tab("Operation Selector", self.list)

        self.dialog.show_all()

        

class OperationList(MainList):
    """
    List of available operations with some handy information
    """

    def __init__(self, parent, size, sidelabel, UItype, tactile): # "Could be common
        MainList.__init__(self, parent, size, sidelabel, UItype)
        self.chooser = []
        if UItype == CREATE:
            self.add_button("Select",self.select)
            self.add_button("Cancel",self.close, True)
            self.chooser += [self.append_list()]
            self.chooser += [self.append_schedule()]
        elif UItype == CLEAR:
            self.add_button("Clear",self.clear)
            self.add_button("Cancel",self.close, True)
            self.chooser += [self.append_clear(tactile)]
        elif UItype == EXECUTE:
            self.add_button("Execute",self.execute)
            self.add_button("Cancel",self.close, True)
            self.chooser += [self.append_clear(tactile)]
        self.show_all()
        
    def select(self, button=None):
        parameters = {}
        for element in self.chooser:
            if element.variable == 'operation':
                parameters[element.variable] = element.getSelected()
            else: # schedule
                parameters[element.variable] = element.getSelected()[0]
        operation, defaults = parameters.pop('operation')
        group = (operation, defaults, parameters)
        executable = []
        short = None
        for item in loader.get_operations():
            if item[0][0] == operation:
                short = item[0][1]['shortname']
                break
        for mp in self.superior.mediapackage:
            if mp.getOpStatus(short) in [0,4,5]:
                executable += [ mp ]
        context.get_worker().enqueue_operations(group, executable) # TODO send a signal better

        self.close(True)

        difference = len(self.superior.mediapackage)-len(executable)
        if difference:
            text = {"title" : "New Operations",
                    "main" : "{0} recording{1} {2} already\nrunning this operation.".format( difference, 
                                                                                                "s" if difference >1 else "",
                                                                                                "are" if difference >1 else "is",
                                                                                                ),
                    "text" : "{0} operation{1} enqueued.".format("No" if not len(executable) else len(executable),
                                                                 "" if len(executable)==1 else "s")
                    }
            buttons = ( gtk.STOCK_OK, gtk.RESPONSE_OK)
            warning = message.PopUp(message.WARNING, text,
                                    context.get_mainwindow(),
                                    buttons)


    def clear(self, button=None):
        options = {}
        for element in self.chooser:
            options[element.variable] = element.getSelected()

        self.close(True)

        text = {"title" : "Clear Operations",
                "main" : "Are you sure?",
                "text" : "The selected operations  will be cancelled."
                }
        buttons = ( "Clear", gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)
        warning = message.PopUp(message.WARNING, text,
                                context.get_mainwindow(),
                                buttons)
        if not warning.response in message.POSITIVE:
            return False
        ops = loader.get_operations()
        for op in options["operation"]:
            for item in ops:
                if item[1] == op:
                    context.get_worker().cancel_nightly_operations( item[0][1]['shortname'], self.superior.mediapackage )

    def execute(self, button=None):
        options = {}
        for element in self.chooser:
            options[element.variable] = element.getSelected()
            
        ops = loader.get_operations()
        for op in options["operation"]:
            for item in ops:
                if item[1] == op:
                    context.get_worker().do_now_nightly_operations( item[0][1]['shortname'], self.superior.mediapackage )

        self.close(True)

    def close(self, button=None): #it's commmon
        self.superior.close()

    def append_list(self):  
        # TODO the list should be available on operations
        """Lists the available operations"""

        available_list = loader.get_operations()
        variable = "operation"
        hprop = self.size[1]/1080.0
        font = int(15 * hprop)
        selectorUI = Chooser(variable,
                             variable.capitalize(),
                             "tree",
                             available_list,
                             preselection = available_list[0],
                             fontsize = font)

        self.pack_start(selectorUI, False, False, 0)
        self.reorder_child(selectorUI,0)
        # TODO selector resize(size)
        return selectorUI

    def append_schedule(self): # TODO get size from class
        variable = "schedule" 
        font = int (15 * self.size[1]/1080.0)
        selectorUI = Chooser(variable,
                             variable.capitalize(),
                             "tree-single", 
                            ["Immediate", "Nightly"],
                             preselection = "Immediate",
                             fontsize = font,
                             )
        self.pack_start(selectorUI, False, False, 0)
        self.reorder_child(selectorUI,1)
        #selectorUI.resize(1)
        return selectorUI

    def append_clear(self, tactile):  
        # TODO the list should be available on operations
        """Lists the available operations"""

        full_list = loader.get_nightly_operations(self.superior.mediapackage)
        available_list = []
        for item in full_list:
            available_list += [ item.get('name') ] 
        if not len(available_list):
            print "No active operations for this packages"
            return None
        font = int (15 * self.size[1]/1080.0)
        variable = "operation"
        selectorUI = Chooser(variable,
                             "Active Operations",
                             "tree-multiple",
                             available_list,
                             preselection = None,                             
                             fontsize = font,
                             extra = tactile )

        self.pack_start(selectorUI, False, False, 0)
        self.reorder_child(selectorUI,0)
        # TODO selector resize(size)
        return selectorUI

gobject.type_register(OperationsUI)