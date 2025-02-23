import os

import pickle
import pymel.core as pm

from logger.logger import Logger


DEFAULT_LIB_PATH = os.path.join(os.path.dirname(__file__), "cons_pickle.pkl")

logger = Logger()
logger.set_propagate(False)

try:
    with open(DEFAULT_LIB_PATH, "rb") as file:
        controllers_dict = pickle.load(file)
        logger.debug(controllers_dict)
        file.close()
except:
    logger.debug(f".pkl file not found ({DEFAULT_LIB_PATH}). Initialising empty 'controllers_dict'...")
    controllers_dict={}


def save_controller(curve=None, curve_name=None):
    """Saves selected NURBS curve (controller) to the pickle file"""
    global controllers_dict

    controller = curve or pm.selected()[0]
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
    
    with open(DEFAULT_LIB_PATH, "wb") as file:
        pickle.dump(controllers_dict, file)
        file.close()


def generate_controller(controller_name=None, scale=1.0):
    """Generate a NURBS curve controller"""

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
            return curve
        else:
            logger.error(f"Controller '{controller_name}' does not exist in the pickle file.")
    else:
        logger.warning("Missing controller name argument...")


def controller_list():
    """Returns a list of stored controllers"""
    return sorted(controllers_dict.keys())
