import clr

clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName('AdWindows')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System')
clr.AddReferenceByPartialName('System.Windows.Forms')

from Autodesk.Revit import DB
from Autodesk.Revit import UI
import Autodesk
import Autodesk.Windows as aw


clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

uiapp = __revit__
# uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = uiapp.ActiveUIDocument
doc = uiapp.ActiveUIDocument.Document

import sys
# sys.path.append("G:\\My Drive\\PythonScripts\\GD_PythonResources\\Revit")
sys.path.append("M:\\600 VWCC\\ARCHITECTURAL\\BIM\\pykTools\\pyKTools\\MyTool.extension\\lib")

from pyrevit import forms
import math
from GetSetParameters import *
from System.Collections.Generic import List
import Selection
import Schedules
from rpw import db
import csv
import GUI
from pyrevit import forms
import Creation
import datetime

# CODE BELOW HERE #

__author__ = "Dolan Klock"

# Tooltip
__doc__ = "This tool sets checks on annotation crop boundary parameter and matches the crop boundary for annotation" \
          " crop boundary of the selected source view to all views with the same scope box as the source view chosen"

def copy_element(element, from_doc, to_doc, transform, copy_options):
    pass


def get_type_name(element, doc):
    """
    This method will take in an element object and get the elements type and then the types name.
    If an element type is passed in as an argument the try block will fail and the except block will
    be executed and retrieve the types name and return it
    :param element: (element object) element whose type name to get
    :return: (String) elements type name
    """
    try:
        element_type_id = element.GetTypeId()
        element_type = doc.GetElement(element_type_id)
        element_parameter_value = element_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
        return element_parameter_value
    except:
        element_parameter_value = element.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
        return element_parameter_value

class Units:
    def decimal_ft_to_mm(val):
        return val * 304.8

def get_floor_thickness(floor): return floor.get_Parameter(DB.BuiltInParameter.FLOOR_ATTR_THICKNESS_PARAM).AsDouble()

def original_floor_thickness(floors): return [get_floor_thickness(floor) for floor in floors]

def floor_height_offset(floor): return floor.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).AsDouble()

def original_floor_height_offset(floors): return [floor_height_offset(floor) for floor in floors]

def get_floors_openings(openings, floor): return [opening for opening in openings if opening.Host.Id == floor.Id]

def main():
    # TODO: copy by selection or by all
    choice = GUI.UI_two_options(title="Copy Structural Slabs For Arch", main_instruction="Copy Structural Slabs", commandlink1="By Selection", commandlink2="By All")
    if choice:
        with forms.WarningBar(title='Select Floors to Copy From Model'):
            linked_floors_copy = uidoc.Selection.PickObjects(Autodesk.Revit.UI.Selection.ObjectType.LinkedElement,
                                                        "Select Floors to Copy From Model")
            link_doc = Selection.get_link_doc()
            element_ids_copy = [ref.LinkedElementId for ref in linked_floors_copy]
            linked_floors_copy = [link_doc.GetElement(e_id) for e_id in element_ids_copy]
    else:
        link_doc = Selection.get_link_doc()
        linked_floors_copy = [floor for floor in DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType()]
        element_ids_copy = []
        floor_level = forms.ask_for_string(prompt="Level name to get floors at")
        type_name_contains = forms.ask_for_string(prompt="Type name contains")
        for floor in linked_floors_copy:
            try:
                level_name = floor.LookupParameter('Level').AsValueString()
            except AttributeError as ex:
                pass
            else:
                if level_name == floor_level:
                    if type_name_contains in get_type_name(floor, link_doc):
                        element_ids_copy.append(floor.Id)
        linked_floors_copy = [link_doc.GetElement(e_id) for e_id in element_ids_copy]

    # getting linked model openings to copy
    linked_openings = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_FloorOpening). \
            WhereElementIsNotElementType()
    # getting the floors height offset from level parameter value for floors being copied
    og_floor_height_offset = original_floor_height_offset(linked_floors_copy)
    # select workset for geometry being copied to be assigned to
    workset = Selection.select_workset(doc, DB.WorksetKind.UserWorkset)
    # elements_copy_list = List[DB.ElementId](element_ids_copy)
    # floor type for copied floors to be assigned to
    floor_type = Selection.Select_floor_type(doc)
    copy_option = GUI.UI_two_options(title="Copy Structural Slabs For Arch", main_instruction="Copy Above Or Below?", commandlink1="Above", commandlink2="Below")
    # getting each floor seleceed for copy by user and that floors openings and copying each set of those elements and appending them to
    # a list for further use
    all_copied_element_ids = []
    with db.Transaction('copying floors and their openings'):
        for floorElement in linked_floors_copy:
            # floorElement = link_doc.GetElement(floor.Id)
            floor_openings = get_floors_openings(linked_openings, floorElement)
            floor_and_openings_copy = [opening.Id for opening in floor_openings]
            floor_and_openings_copy.append(floorElement.Id)
            floor_and_openings_copy_list = List[DB.ElementId](floor_and_openings_copy)
            copied_elements_openings_floors = DB.ElementTransformUtils.CopyElements(link_doc, floor_and_openings_copy_list, doc, None ,DB.CopyPasteOptions())
            all_copied_element_ids.append(copied_elements_openings_floors)
    # getting floor elements and opening elements in combined list
    flat_list = [item for sublist in all_copied_element_ids for item in sublist]
    # copied_elements = DB.ElementTransformUtils.CopyElements(link_doc, elements_copy_list, doc, None ,DB.CopyPasteOptions())
    copied_elements = filter(lambda e: doc.GetElement(e).Category.Name == "Floors", flat_list)
    # getting original floor thicknesses
    og_floor_thickness = original_floor_thickness([doc.GetElement(e_id) for e_id in copied_elements])
    # og_floor_height_offset = original_floor_height_offset(link_doc.GetElement(e_id) for e_id in element_ids_copy)
    # setting copied floors workset & comment parameter
    for e_id, og_thickness, og_offset in zip(copied_elements, og_floor_thickness, og_floor_height_offset):
        element = doc.GetElement(e_id)
        e_workset_param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        e_comment_param = element.LookupParameter('Comments')
        # setting workset
        SetParameter.set_element_workset(element, workset)
        # setting new floor type
        SetParameter.set_type(element, floor_type.Id.IntegerValue)
        with db.Transaction('setting comment parameter'):
            # setting comment parameter
            e_comment_param.Set(str(datetime.datetime.now()))
            # setting height offset param
            e_height_offset_param = element.LookupParameter('Height Offset From Level')
            e_height_offset = element.LookupParameter('Height Offset From Level').AsInteger()
            if copy_option:
                e_height_offset_param.Set(og_offset + get_floor_thickness(element))
            else:
                e_height_offset_param.Set(og_offset - og_thickness)
    # TODO: ask user if they want to copy above or below select copied slabs?
    #  if above need to offset up the thickness of the copied floor
                
if __name__ == '__main__':
    main()

# TODO: when copy floors if level in linked model copying from does not exist then a different level the floor is copied to which affects location 
#  slab is coped to, (hydro vaults) - need to figure out level difference and update difference ...?
  
# TODO: should make a way to copy slabs by slab name contains "slab" as example









































# import clr

# clr.AddReferenceByPartialName('PresentationCore')
# clr.AddReferenceByPartialName('AdWindows')
# clr.AddReferenceByPartialName("PresentationFramework")
# clr.AddReferenceByPartialName('System')
# clr.AddReferenceByPartialName('System.Windows.Forms')

# from Autodesk.Revit import DB
# from Autodesk.Revit import UI
# import Autodesk
# import Autodesk.Windows as aw


# clr.AddReference("RevitServices")
# import RevitServices
# from RevitServices.Persistence import DocumentManager
# from RevitServices.Transactions import TransactionManager

# uiapp = __revit__
# # uiapp = DocumentManager.Instance.CurrentUIApplication
# app = uiapp.Application
# uidoc = uiapp.ActiveUIDocument
# doc = uiapp.ActiveUIDocument.Document

# import sys
# # sys.path.append("G:\\My Drive\\PythonScripts\\GD_PythonResources\\Revit")
# sys.path.append("M:\\600 VWCC\\ARCHITECTURAL\\BIM\\pykTools\\pyKTools\\MyTool.extension\\lib")

# from pyrevit import forms
# import math
# from GetSetParameters import *
# from System.Collections.Generic import List
# import Selection
# import Schedules
# from rpw import db
# import csv
# import GUI
# from pyrevit import forms
# import Creation
# import datetime

# # CODE BELOW HERE #

# __author__ = "Dolan Klock"

# # Tooltip
# __doc__ = "This tool sets checks on annotation crop boundary parameter and matches the crop boundary for annotation" \
#           " crop boundary of the selected source view to all views with the same scope box as the source view chosen"

# def copy_element(element, from_doc, to_doc, transform, copy_options):
#     pass


# def get_type_name(element, doc):
#     """
#     This method will take in an element object and get the elements type and then the types name.
#     If an element type is passed in as an argument the try block will fail and the except block will
#     be executed and retrieve the types name and return it
#     :param element: (element object) element whose type name to get
#     :return: (String) elements type name
#     """
#     try:
#         element_type_id = element.GetTypeId()
#         element_type = doc.GetElement(element_type_id)
#         element_parameter_value = element_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
#         return element_parameter_value
#     except:
#         element_parameter_value = element.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
#         return element_parameter_value

# class Units:
#     def decimal_ft_to_mm(val):
#         return val * 304.8

# def get_floor_thickness(floor): return floor.get_Parameter(DB.BuiltInParameter.FLOOR_ATTR_THICKNESS_PARAM).AsDouble()

# def original_floor_thickness(floors): return [get_floor_thickness(floor) for floor in floors]

# def floor_height_offset(floor): return floor.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).AsDouble()

# def original_floor_height_offset(floors): return [floor_height_offset(floor) for floor in floors]

# def get_floors_openings(openings, floor): return [opening for opening in openings if opening.Host.Id == floor.Id]

# def main():
#     # TODO: copy by selection or by all
#     choice = GUI.UI_two_options(title="Copy Structural Slabs For Arch", main_instruction="Copy Structural Slabs", commandlink1="By Selection", commandlink2="By All")
#     if choice:
#        with forms.WarningBar(title='Select Floors to Copy From Model'):
#         linked_floors_copy = uidoc.Selection.PickObjects(Autodesk.Revit.UI.Selection.ObjectType.LinkedElement,
#                                                    "Select Floors to Copy From Model")
#         element_ids_copy = [ref.LinkedElementId for ref in linked_floors_copy]
#         link_doc = Selection.get_link_doc()
#     else:
#         link_doc = Selection.get_link_doc()
#         linked_floors_copy = [floor for floor in DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType()]
#         element_ids_copy = []
#         floor_level = forms.ask_for_string(prompt="Level name to get floors at")
#         type_name_contains = forms.ask_for_string(prompt="Type name contains")
#         for floor in linked_floors_copy:
#             try:
#                 level_name = floor.LookupParameter('Level').AsValueString()
#             except AttributeError as ex:
#                 pass
#             else:
#                 if level_name == floor_level:
#                     if type_name_contains in get_type_name(floor, link_doc):
#                         element_ids_copy.append(floor.Id)
#         linked_floors_copy = [link_doc.GetElement(e_id) for e_id in element_ids_copy]

#     # getting linked model openings to copy
#     linked_openings = DB.FilteredElementCollector(link_doc).OfCategory(DB.BuiltInCategory.OST_FloorOpening). \
#             WhereElementIsNotElementType()
#     # getting the floors height offset from level parameter value for floors being copied
#     og_floor_height_offset = original_floor_height_offset(link_doc.GetElement(e_id) for e_id in element_ids_copy)
#     # select workset for geometry being copied to be assigned to
#     workset = Selection.select_workset(doc, DB.WorksetKind.UserWorkset)
#     # elements_copy_list = List[DB.ElementId](element_ids_copy)
#     # floor type for copied floors to be assigned to
#     floor_type = Selection.Select_floor_type(doc)
#     copy_option = GUI.UI_two_options(title="Copy Structural Slabs For Arch", main_instruction="Copy Above Or Below?", commandlink1="Above", commandlink2="Below")
#     # getting each floor seleceed for copy by user and that floors openings and copying each set of those elements and appending them to
#     # a list for further use
#     all_copied_element_ids = []
#     with db.Transaction('copying floors and their openings'):
#         for floor in linked_floors_copy:
#             floorElement = link_doc.GetElement(floor.Id)
#             floor_openings = get_floors_openings(linked_openings, floorElement)
#             floor_and_openings_copy = [opening.Id for opening in floor_openings]
#             floor_and_openings_copy.append(floorElement.Id)
#             floor_and_openings_copy_list = List[DB.ElementId](floor_and_openings_copy)
#             copied_elements_openings_floors = DB.ElementTransformUtils.CopyElements(link_doc, floor_and_openings_copy_list, doc, None ,DB.CopyPasteOptions())
#             all_copied_element_ids.append(copied_elements_openings_floors)
#     # getting floor elements and opening elements in combined list
#     flat_list = [item for sublist in all_copied_element_ids for item in sublist]
#     # copied_elements = DB.ElementTransformUtils.CopyElements(link_doc, elements_copy_list, doc, None ,DB.CopyPasteOptions())
#     copied_elements = filter(lambda e: doc.GetElement(e).Category.Name == "Floors", flat_list)
#     # getting original floor thicknesses
#     og_floor_thickness = original_floor_thickness([doc.GetElement(e_id) for e_id in copied_elements])
#     # og_floor_height_offset = original_floor_height_offset(link_doc.GetElement(e_id) for e_id in element_ids_copy)
#     # setting copied floors workset & comment parameter
#     for e_id, og_thickness, og_offset in zip(copied_elements, og_floor_thickness, og_floor_height_offset):
#         element = doc.GetElement(e_id)
#         e_workset_param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
#         e_comment_param = element.LookupParameter('Comments')
#         # setting workset
#         SetParameter.set_element_workset(element, workset)
#         # setting new floor type
#         SetParameter.set_type(element, floor_type.Id.IntegerValue)
#         with db.Transaction('setting comment parameter'):
#             # setting comment parameter
#             e_comment_param.Set(str(datetime.datetime.now()))
#             # setting height offset param
#             e_height_offset_param = element.LookupParameter('Height Offset From Level')
#             e_height_offset = element.LookupParameter('Height Offset From Level').AsInteger()
#             if copy_option:
#                 e_height_offset_param.Set(og_offset + get_floor_thickness(element))
#             else:
#                 e_height_offset_param.Set(og_offset - og_thickness)
#     # TODO: ask user if they want to copy above or below select copied slabs?
#     #  if above need to offset up the thickness of the copied floor
                
# if __name__ == '__main__':
#     main()

# # TODO: when copy floors if level in linked model copying from does not exist then a different level the floor is copied to which affects location 
# #  slab is coped to, (hydro vaults) - need to figure out level difference and update difference ...?
  
# # TODO: should make a way to copy slabs by slab name contains "slab" as example