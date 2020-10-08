##################################################################
##                                                              ##
## GameSaver - a module for loading and saving game files       ##
## v1.5                                                         ##
##                                                              ##
##################################################################
##                                                              ##
## Original version (1.0-1.5) written by                        ##
## Ian Eborn (Thaumaturge) in 2012-2020                         ##
##                                                              ##
##################################################################
##                                                              ##
## This code is free for both commercial and private use.       ##
## Please leave the above credits in any subsequent versions    ##
## This module and related files are offered as-is, without any ##
## warranty, with any and all defects or errors.                ##
##                                                              ##
##################################################################

import types, collections, codecs, builtins

from direct.stdpy.file import *

class SpecialTypeEntry(object):
    """A class that holds the callback functions used
    to get a saveable representation of a given type
    and to restore one from such a representation"""

    def __init__(self, restoreFn, saveFn):
        self.restoreFn = restoreFn
        self.saveFn = saveFn

class SaveableObject(object):
    """The base class for objects that can be saved, aside
    from simple types (int, float, str, etc.) and types
    held in the "special types" dictionary.
    Classes that should save non-trivial data should
    most likely inherit from this class"""
    
    def getSaveData(self, forLevelSave):
        """Retrieve a GameSaveEntry for the given object
        that holds the data to be saved for that object.
        
        Params: forLevelSave -- Whether this save data
                                is intended for a level file, as
                                opposed to a save of an active game."""
                                
        result = GameSaveEntry()
        result.objType = self.__class__.__name__
        
        return result
    
    def loadFromSaveData(self, data, refObj):
        """Restore the object from the given data
        
        Params: data -- The save data for this object
                refObj -- An object to be passed on to
                          the object in the case of
                          a callback having been specified"""
                        
        if data is None:
            return
        for datum in data.dataList:
            newVal = datum.dataList
            newVal = self.reconstructObject(newVal, datum.objType)
            if datum.loadFn.rstrip().endswith("="):
                setattr(self, datum.loadFn.rstrip()[:-1].rstrip(), newVal)
            else:
                getattr(self, datum.loadFn)(newVal, refObj)
    
    def reconstructObject(self, newVal, objType):
        """An internal method used to actually construct the
        desired object.
        
        Params: newVal -- Data describing the object
                objType -- The class of the object"""
                
        notFoundInSpecialTypes = True
        i = 0
        keys = list(GameSaver.specialTypeDictionary.keys())
        while i < len(keys) and notFoundInSpecialTypes:
            if GameSaver.isSubclass(objType, keys[i]):
                if len(newVal) == 1:
                    newVal = newVal[0]
                typeEntry = GameSaver.specialTypeDictionary[keys[i]]
                newVal = typeEntry.restoreFn(newVal)
                notFoundInSpecialTypes = False
            i += 1
        if notFoundInSpecialTypes:
            if objType == list.__name__:
                newVal = self.reconstructList(newVal)
            elif objType == tuple.__name__:
                newVal = self.reconstructTuple(newVal)
            elif objType == dict.__name__:
                newVal = self.reconstructDictionary(newVal)
            else:
                if len(newVal) == 1:
                    newVal = newVal[0]
                if objType == bool.__name__:
                    if isinstance(newVal, str):
                        newVal = newVal.lower()
                        if newVal == "true" or newVal == "1":
                            newVal = True
                        else:
                            newVal = False
                    newVal = bool(newVal)
                elif objType == type(None).__name__ or objType == "None":
                    newVal = None
                elif objType == GameSaveEntry.__name__:
                    retVal = GameSaveEntry()
                    retVal.objType = objType
                    if isinstance(newVal, list):
                        retVal.dataList = newVal
                    else:
                        retVal.dataList = [newVal]
                    newVal = retVal
                elif objType == str.__name__:
                    newVal = bytes(newVal, "utf-8").decode("utf-8")
                elif objType == bytes.__name__:
                    newVal = codecs.escape_decode(newVal)[0]
                elif objType == int.__name__:
                    newVal = int(newVal)
                elif objType == float.__name__:
                    newVal = float(newVal)
                else:
                    if objType == types.FunctionType.__name__ or \
                       objType == types.MethodType.__name__:
                        raise IOError("Loading: GameSaver cannot save methods or functions; the method or function in question is:", newVal)
                    else:
                        raise IOError("Loading: Attempt to construct unrecognised class! Class-name:", objType)
        return newVal
    
    def reconstructList(self, listData):
        """An internal method used to reconstruct a list.
        
        Params: listData -- The data for the list"""
        
        result = []
        
        for element in listData:
            result.append(self.reconstructObject(element.dataList, element.objType))
        
        return result
    
    def reconstructTuple(self, listData):
        """An internal method used to reconstruct a tuple.
        
        Params: listData -- The data for the tuple"""
        
        temp = []
        
        for element in listData:
            temp.append(self.reconstructObject(element.dataList, element.objType))

        result = tuple((val for val in temp))
        return result
    
    def reconstructDictionary(self, listData):
        """An internal method used to reconstruct a dictionary.
        
        Params: listData -- The data for the dictionary"""
        
        result = {}
        
        for element in listData:
            tuple = self.reconstructObject(element.dataList, element.objType)
            result[tuple[0]] = tuple[1]
        
        return result

class SaveableWrapper(SaveableObject):
    """ A convenience class used to save simple non-SaveableObject objects,
        such as Python dictionaries or lists
    
    To save an object using this class:
     - Create an instance of the class.
     - Copy the object to be saved into the
       instance's 'data' variable, below.
     - Save the instance using GameSaver, as usual.
    
    To load the object again:
     - Create an instance of the class.
     - Load the relevant file using GameSaver, as usual.
     - Restore the saved wrapper into the instance, as with
       any other SaveableObject.
     - Copy the object from the 'data' variable below."""
    
    def __init__(self):
        self.data = None
    
    def getSaveData(self, forLevelSave):
        result = GameSaveEntry()
        
        result.addItem("data = ", self.data)
        
        return result

class GameSaveEntry(object):
    """A class that holds a description of a given object to be saved or restored."""

    repr_counter = 0
    
    def __init__(self):
        self.objType = self.__class__.__name__
        self.loadFn = None
        self.dataList = []
    
    def addItem(self, loadFn, obj, index = None):
        """Add a piece of data to the object's description.
        
        Params: loadFn -- A string command used in restoring the data
                          to its object. For simple types, an assignment
                          statement is allowed, excluding the "self" prefix.
                          Otherwise, give the name of a method to be called.
                obj -- The data to be saved."""
                
        newEntry = GameSaveEntry()
        newEntry.objType = obj.__class__.__name__
        newEntry.loadFn = loadFn
        # These next two could probably be handled via map and a lambda,
        # but that seems to me to be less readable than the for-loops below,
        # and if not constructed carefully seems to potentially lead to
        # infinite loops...
        if isinstance(obj, dict):
            for pair in list(obj.items()):
                newEntry.addItem("", pair)
        # I'm excluding "str" here because we write our data as strings,
        # and a str is, naturally, already a string, making it seem wasteful
        # to individually add each character; additionally, there is some
        # logic that is specfic to str -- see the final "else" below.
        elif isinstance(obj, collections.Iterable) and not isinstance(obj, str) and not isinstance(obj, bytes):
            for item in obj:
                newEntry.addItem("", item)
        elif callable(obj):
            newEntry.dataList.append(obj.__name__)
        elif isinstance(obj, GameSaveEntry):
            newEntry.dataList += obj.dataList
            newEntry.objType = obj.objType
        else:
            if isinstance(obj, str):
                #obj = obj.replace("\n", "\\n")
                obj = obj.encode("unicode_escape")
                newEntry.dataList.append(obj)
            elif isinstance(obj, bytes):
                convertedVal = codecs.escape_encode(obj)[0]
                newEntry.dataList.append(convertedVal)
            else:
                notFoundSpecialType = True
                i = 0
                keys = list(GameSaver.specialTypeDictionary.keys())
                while i < len(keys) and notFoundSpecialType:
                    if isinstance(obj, keys[i]):
                        notFoundSpecialType = False
                        newEntry.addItem("", GameSaver.specialTypeDictionary[keys[i]].saveFn(obj))
                    i += 1
                if notFoundSpecialType:
                    newEntry.dataList.append(str(obj))
        if index is None:
            self.dataList.append(newEntry)
        else:
            self.dataList.insert(index, newEntry)
    
    def __repr__(self):
        """A convenience method allowing for formatted printing of GameSaveEntries"""
        
        GameSaveEntry.repr_counter += 1
        result = "\n"
        for i in range(GameSaveEntry.repr_counter*2):
            result += " "
        result += "Game Save Entry: " + str(self.objType) + " " + str(self.loadFn) + "\n"
        for datum in self.dataList:
            for i in range(GameSaveEntry.repr_counter*2):
                result += " "
            result += str(datum) + "\n"
        GameSaveEntry.repr_counter -= 1
        return result

class GameSaver(object):
    """The core class of the module.
    GameSaver's methods are static; the class is not intended to be instantiated"""

    ENTRY_MARKER = "ENTRY"
    
    """Classes that are not simple types (int, float, str, etc.), but which
    are also not descendants of SaveableObject, are stored in this dictionary;
    they may be registered by calling "addSpecialType"."""
    specialTypeDictionary = {}
    
    """A function callback used to check the inheritance of a class;
    the callback is used to allow for the checking of classes that
    GameSaver doesn't know about, such as custom game classes."""
    isSubclass = None
    
    def __init__(self):
        raise RuntimeError("GameSaver is a static class; it is not intended to be instantiated!")
    
    @staticmethod
    def addSpecialType(type, restoreFn, saveFn):
        """Register a special type
        
        Params: restoreFn -- The function to call to restore an object
                saveFn -- The function to call to get a saveable
                          representation of an object"""
                        
        GameSaver.specialTypeDictionary[type] = SpecialTypeEntry(restoreFn, saveFn)
    
    @staticmethod
    def writeLine(line, fileObj):
        """Write a newline-terminated line of text to a file.
        
        Params: line -- The text to write
                fileObj -- The file object to write to"""
                
        if not isinstance(line, str):
            if isinstance(line, bytes):
                try:
                    line = line.decode("utf-8")
                except UnicodeDecodeError:
                    line = str(line)
            else:
                line = str(line)
        if not line.endswith("\n"):
            line += "\n"
        fileObj.write(line)
    
    @staticmethod
    def readLine(fileObj):
        """Read a newline-terminated line of text from a file.
        
        Params: fileObj -- The file object to read from
        
        Returns: The line of text read, sans final newline, if any"""
    
        result = fileObj.readline()
        if result.endswith("\n"):
            result = result[0:len(result)-1]
        return result
    
    @staticmethod
    def writeEntry(obj, fileObj):
        """Write a GameSaveEntry to file.
        
        Params: obj -- The GameSaveEntry to write.
                fileObj -- The file object to write to."""
    
        GameSaver.writeLine(obj.objType, fileObj)
        GameSaver.writeLine(obj.loadFn, fileObj)
        GameSaver.writeLine(len(obj.dataList), fileObj)
        for datum in obj.dataList:
            if isinstance(datum, GameSaveEntry):
                GameSaver.writeLine(GameSaver.ENTRY_MARKER, fileObj)
                GameSaver.writeEntry(datum, fileObj)
            else:
                GameSaver.writeLine(datum, fileObj)
    
    @staticmethod
    def readEntry(fileObj):
        """Read a GameSaveEntry from file.
        
        Note: This method is recursive; if a GameSaveEntry's
              representation indicates that it contains
              another GameSaveEntry, the method should call itself
              for that new entry and include it within the return
              value.
            
        Params: fileObj -- The file object to read from.
        
        Returns: A GameSaveEntry with whatever data was read."""
    
        result = GameSaveEntry()
        type = GameSaver.readLine(fileObj)
        loadFn = GameSaver.readLine(fileObj)
        result.objType = type
        result.loadFn = loadFn
        numItems = int(GameSaver.readLine(fileObj))
        for i in range(numItems):
            input = GameSaver.readLine(fileObj)
            if input == GameSaver.ENTRY_MARKER:
                input = GameSaver.readEntry(fileObj)
            result.dataList.append(input)
        return result
    
    @staticmethod
    def saveGame(baseObjToSave, fileName, forLevelSave):
        """Save an object to file.
        
        Params: baseObjToSave -- The object to be saved.
                fileName -- The name of the file to write to.
                forLevelSave -- Whether this save data
                                is intended for a level file, as
                                opposed to a save of an active game."""
    
        fileObj = None
        objList = baseObjToSave.getSaveData(forLevelSave)
        ## To do: This should probably just throw to exception and let it
        ##        be caught or passed on by the calling method.
        try:
            fileObj = open(fileName, "w")
            GameSaver.writeEntry(objList, fileObj)
        except IOError:
            print("Saving: IOError!  Failed to open file \"" + fileName + "\"!")
            raise
        else:
            if fileObj is not None:
                fileObj.close()
    
    @staticmethod
    def loadGame(fileName):
        """Load an object from file.
        
        Params: fileName -- The name of the file to read from.
        
        Returns: A GameSaveEntry describing the object represented
                 by the file."""
    
        result = None
        fileObj = None
        try:
            fileObj = open(fileName, "r")
            result = GameSaver.readEntry(fileObj)
        except IOError:
            print("Loading: IOError!  Failed to open file \"" + fileName + "\"!")
            raise
        else:
            if fileObj is not None:
                fileObj.close()
        
        return result
    
    @staticmethod
    def destroy():
        """Clean up GameSaveEntry's data, in particular the function
        objects that it holds for special types and subclass-checking."""
    
        for key in list(GameSaver.specialTypeDictionary.keys()):
            GameSaver.specialTypeDictionary[key] = None
        GameSaver.specialTypeDictionary = {}
        GameSaver.isSubclass = None
