##################################################################
##                                                              ##
## A simple game demonstration of GameSaver                     ##
##                                                              ##
##################################################################
##                                                              ##
## Original version written by                                  ##
## Ian Eborn (Thaumaturge) in 2013                              ##
##                                                              ##
##################################################################
##                                                              ##
## This code is free for both commercial and private use.       ##
## Please leave the above credits in any subsequent versions    ##
## This module and related files are offered as-is, without any ##
## warranty, with any and all defects or errors.                ##
##                                                              ##
##################################################################

# I currently don't see a means of getting around Panda's
# proliferation of vector classes. :/
from panda3d.core import VBase3, LVector3f, Vec3

from direct.showbase.DirectObject import DirectObject
import direct.directbase.DirectStart

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
from direct.gui.DirectGui import *

from GameSaver.GameSaver import SaveableObject, GameSaveEntry, GameSaver

import sys, random

import inspect

# This method is used by GameSaver to check whether a given object
# is a subclass of the given class; it's defined here because
# GameSaver might not know about classes that you've defined.
@staticmethod
def isSubclass(name, classToCheck):
    if name == "NoneType" or name == "function" or name == "method":
        return False
    if not name in masterClassDict:
        return False
    return issubclass(masterClassDict[name], classToCheck)

class Tester(DirectObject, SaveableObject):
    def __init__(self):
        # Some intialisation of the GameSaver
        # This should onlybe done once, unless
        #  you want to change something!
        ## I dislike Panda's separation of "Points" from "Vectors",
        ## so I'm conflating them here.
        GameSaver.addSpecialType(VBase3, self.makeVectorFromSave, self.getVectorForSave)
        GameSaver.isSubclass = isSubclass
        
        # Some arbitrary data to save and load
        self.testInt = random.randint(0, 20)
        self.testList = []
        for i in range(random.randint(4, 8)):
            self.testList.append(random.uniform(0, 5))
        self.testString = random.choice(["kittens", "meteor", "magic", "Kittens and meteors\nare magic!\n:D"])
        self.testVec = Vec3(random.uniform(-1, 1),
                            random.uniform(-1, 1),
                            random.uniform(-1, 1))
        self.testDict = {}
        keyList = ["keycard", "ornate", "iron", "gold", "skeleton"]
        for i in range(5):
            key = keyList.pop(0)
            value = random.choice([True, False])
            self.testDict[key] = value
        
        # Interface
        self.accept("escape", sys.exit)
        
        self.saveButton = DirectButton(text = "Save",
                                      command=self.save,
                                      scale = 0.05,
                                      pos = (0, 0, 0.9))
        self.loadButton = DirectButton(text = "Load",
                                      command=self.load,
                                      scale = 0.05,
                                      pos = (0, 0, 0.8))
        
        self.instructionDisplay = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(0, 0.7, 0),
                             align=TextNode.ACenter, scale = .05, text="Press Escape to quit")
        
        self.saveDisplay = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(-1.2, 0.9, 0),
                             align=TextNode.ALeft, scale = .05, mayChange = 1)
        self.loadDisplay = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(1.2, 0.9, 0),
                             align=TextNode.ARight, scale = .05, mayChange = 1)
    
    def save(self):
        succeeded = False
        try:
            GameSaver.saveGame(self, "simpleTest.txt", False)
            succeeded = True
        except IOError:
            self.saveDisplay["text"] = "Failed to save game!"
        
        if succeeded:
            self.setText(self.saveDisplay, "Saved:\n")
            
            # Clear the object's values so that we see that
            # they were loaded after pressing the "load" button
            self.testInt = 0
            self.testList = []
            self.testString = ""
            self.testVec = Vec3(0, 0, 0)
            self.testDict = {}
            self.setText(self.loadDisplay, "Values cleared:\n")
    
    def load(self):
        # GameSaver.loadGame should return a GameSaveEntry
        # holding the loaded data; this is then passed on to
        # the "loadFromSaveData" method of the relevant object
        try:
            result = GameSaver.loadGame("simpleTest.txt")
            self.loadFromSaveData(result, self)
            self.setText(self.loadDisplay, "Loaded:\n")
        except IOError:
            self.loadDisplay["text"] = "Failed to load save file!"
    
    def setText(self, textObj, prefix):
        # Arrange some text into the specified OnScreenText object
        listStr = "\n[\n"
        vecStr = ""
        for val in self.testList:
            listStr += "{0:.2f}\n".format(val)
        listStr += "]"
        vecStr = "Vector: ({0[0]:.2f}, {0[1]:.2f}, {0[2]:.2f})".format(self.testVec)
        dictStr = "\n{\n"
        for key, val in list(self.testDict.items()):
            dictStr += key + " : " + str(val) + "\n"
        dictStr += "}"
        textObj["text"]=prefix+\
                        "\nInt: "+str(self.testInt)+\
                        "\nList: "+listStr+\
                        "\nString: "+self.testString+\
                        "\nVector: "+vecStr+\
                        "\nDict: "+dictStr
    
    # This method is originally defined in SaveableObject;
    # it provides to GameSaver the data that you want to save.
    def getSaveData(self, forLevelSave):
        # I strongly recommend getting the GameSaveEntry object
        # that you work with from the parent class, even if that's
        # just SaveableObject. This allows the system the
        # opportunity to get save data defined in parent classes
        # and allows the SaveableObject class to perform
        # some initialisation
        # See the Enemy class for an example.
        result = SaveableObject.getSaveData(self, forLevelSave)
        
        #Note that we omit the "self." in the first parameter
        result.addItem("testInt = ", self.testInt)
        result.addItem("testList =", self.testList)
        result.addItem("testString = ", self.testString)
        result.addItem("testVec = ", self.testVec)
        result.addItem("testDict = ", self.testDict)

        # Don't forget to return the result!
        return result
    
    ## Methods for the construction of types that are not
    ## simple types, but which do not derive from SaveableObject
    
    ### Vectors will simply be stored as tuples
    def getVectorForSave(self, vec):
        return (vec[0], vec[1], vec[2])
    
    def makeVectorFromSave(self, description):
        x = description.dataList[0].dataList[0]
        y = description.dataList[1].dataList[0]
        z = description.dataList[2].dataList[0]
        return Vec3(float(x), float(y), float(z))


# A dictionary of classes known to the game, for use
# when determining subclassing
masterClassDict = {x[0] : x[1] for x in inspect.getmembers(sys.modules[__name__], inspect.isclass)}

tester = Tester()

run()