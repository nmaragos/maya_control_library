import os

import pickle
import pymel.core as pm
import maya.OpenMaya as om
import maya.OpenMayaUI as omui
from PIL import Image

import constants
from logger.logger import Logger

logger = Logger()
logger.set_level("INFO")
logger.set_propagate(False)

try:
    with open(constants.DEFAULT_LIB_PATH, "rb") as file:
        controllers_dict = pickle.load(file)
        logger.debug(controllers_dict)
except:
    logger.debug(f".pkl file not found ({constants.DEFAULT_LIB_PATH}). Initialising empty 'controllers_dict'...")
    controllers_dict={}


def save_controller(curve=None, curve_name=None, create_icon=False):
    """Saves selected NURBS curve (controller) to the library.
    
    Args:
        curve (nt.Transform): The Maya curve node to be saved in the library.
        curve_name (str): The name of the controller
        create_icon (bool): Whether or not to create a corresponding icon file.
    """
    global controllers_dict

    controller = curve or pm.selected()[0]
    if not controller:
        return
    
    controller_shape = controller.getShape()

    controller_name = curve_name or pm.promptBox("Controller name", "Please enter a name:", "Ok", "Cancel")
    if not controller_name:
        return
    
    logger.debug(f"Controller name: {controller_name}")
    
    controllers_dict[controller_name] = {
        "cvs": [tuple(cv) for cv in controller_shape.getCVs()],
        "degree": controller_shape.degree(),
        "form": controller_shape.form().key,
        "knots": controller_shape.getKnots(),
        "spans": controller_shape.spans.get(),        
    }

    if create_icon:
        viewport_snip(controller_name)
    
    with open(constants.DEFAULT_LIB_PATH, "wb") as file:
        pickle.dump(controllers_dict, file)

def delete_controller(controller_name):
    """Delete a controller from the library.

    Args:
        controller_name (str): The name of the controller to be removed.    
    """
    with open(constants.DEFAULT_LIB_PATH, "rb") as file:
        controllers_dict = pickle.load(file)
    
    if controller_name in controllers_dict:
        del controllers_dict[controller_name]
        with open(constants.DEFAULT_LIB_PATH, "wb") as file:
            pickle.dump(controllers_dict, file)

        icon_filepath = os.path.join(constants.ICONS_FOLDER, f"{controller_name}.png")
        if os.path.isfile(icon_filepath):
            os.remove(icon_filepath)

def load_controller(controller_name=None, scale=1.0, colour=0):
    """Generate a NURBS curve in Maya according to the selected controller.
    
    Args:
        controller_name (str): The name of the cotroller in the library.
        scale (float): The scale amount of the new controller.
        colour (int): The colour (according to Maya standards) of the new controller.

    Returns:
        curve (nt.Transform): The newlly created curve.
    """

    if controller_name:
        control_to_create = controllers_dict.get(controller_name, None)
        logger.debug(control_to_create)
        if control_to_create:
            cvs = control_to_create.get("cvs")
            degree = control_to_create.get("degree")
            knots = control_to_create.get("knots")
            periodic = True if control_to_create.get("form") == "periodic" else False
            curve = pm.curve(d=degree, p=cvs, k=knots, per=periodic, n=controller_name)
            curve.scale.set((scale, scale, scale))
            pm.makeIdentity(apply=True, t=False, r=False, s=True)
            if colour:
                curve.getShape().overrideEnabled.set(True)
                curve.getShape().overrideColor.set(colour)
            return curve
        else:
            logger.error(f"Controller '{controller_name}' does not exist in the pickle file.")
    else:
        logger.warning("Missing controller name argument...")


def controller_list():
    """Returns a list of stored controllers"""
    return sorted(controllers_dict.keys())


def viewport_snip(name, crop_size=240):
    """Capture an image of Maya's active viewport, crop it and save it as .png file."
    
    Args:
        name (str): The filename of image file.
        crop_size (int): The size, in pixels, of the final image. Currently set as square crop ratio.
    """
    view = omui.M3dView.active3dView()
    img = om.MImage()

    view.readColorBuffer(img, True)

    icon_filename = os.path.join(constants.ICONS_FOLDER, f"{name}.png")
    img.writeToFile(icon_filename, "png")

    image = Image.open(icon_filename)
    image_width, image_height = image.size

    left = (image_width - crop_size) / 2
    top = (image_height - crop_size) / 2
    right = (image_width + crop_size) / 2
    bottom = (image_height + crop_size) / 2

    cropped_image = image.crop((left, top, right, bottom))
    cropped_image.save(icon_filename)
