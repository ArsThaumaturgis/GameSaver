##################################################################
##                                                              ##
## A simple game designed to demonstrate GameSaver              ##
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

from panda3d.core import Vec3, Vec4, Point3, Point2, PandaNode, NodePath
from panda3d.core import VBase4, VBase3, VBase2, LVecBase2, LVecBase3, LVecBase3f, LVecBase4f, LVector3f, LVector2f, LPoint3f, LPoint2f
from panda3d.core import ColorBlendAttrib, TransparencyAttrib, CardMaker
from panda3d.core import DirectionalLight, PointLight
from direct.showbase.DirectObject import DirectObject
from direct.interval.IntervalGlobal import *
from direct.task import Task
import direct.directbase.DirectStart
import os, sys, math, random, datetime

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
from direct.gui.DirectGui import *

from GameSaver.GameSaver import SaveableObject, GameSaveEntry, GameSaver

import inspect


# Constants used by our game
FRICTION = 2.0
LEVEL_END_DURATION = 5.0
WAVE_DELAY = 0.7
SAVE_GAME_FILE = "SAVE_GAME.txt"


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

class Game(DirectObject, SaveableObject):
    def __init__(self):
        base.disableMouse()
        base.camera.setPos(0, -10.0, 0)
        base.win.setClearColor(Vec4(0, 0, 0, 1))
        
        # Some intialisation of the GameSaver
        # This should onlybe done once, unless
        #  you want to change something!
        GameSaver.addSpecialType(GameObject, self.getGameObjectFromSave, self.getGameObjectID)
        ## I dislike Panda's separation of "Points" from "Vectors",
        ## so I'm conflating them here.
        GameSaver.addSpecialType(VBase4, self.makeVector4FromSave, self.getVector4ForSave)
        GameSaver.addSpecialType(VBase3, self.makeVectorFromSave, self.getVectorForSave)
        GameSaver.addSpecialType(VBase2, self.makeVector2FromSave, self.getVector2ForSave)
        GameSaver.isSubclass = isSubclass
        
        # Game input
        self.accept("escape", sys.exit)
        
        self.accept("w", self.setKey, ["up", True])
        self.accept("w-up", self.setKey, ["up", False])
        self.accept("s", self.setKey, ["down", True])
        self.accept("s-up", self.setKey, ["down", False])
        self.accept("a", self.setKey, ["left", True])
        self.accept("a-up", self.setKey, ["left", False])
        self.accept("d", self.setKey, ["right", True])
        self.accept("d-up", self.setKey, ["right", False])
        
        self.accept("space", self.setKey, ["fire", True])
        self.accept("space-up", self.setKey, ["fire", False])
        
        self.keys = {"up":False, "down":False, "left":False, "right":False, "fire":False}
        
        # GUI
        self.saveButton = DirectButton(text = "Save Game",
                                      command=self.save,
                                      scale = 0.05,
                                      pos = (0.5, 0, 0.9))
        self.loadButton = DirectButton(text = "Load Game",
                                      command=self.load,
                                      scale = 0.05,
                                      pos = (0.8, 0, 0.9))
        
        self.instructions = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(-1, 0.9, 0),
                             align=TextNode.ALeft, scale = .05,
                             text="Movement: W,A,S,D\nFire: Space\nQuit: Escape")
        self.levelText = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(0, 0.9, 0),
                             align=TextNode.ACenter, scale = .05, mayChange = 1,
                             text="Level 0")
        self.waveText = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(0, 0.8, 0),
                             align=TextNode.ACenter, scale = .05, mayChange = 1,
                             text="Waves left: 0")
        self.levelEndText = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(0, 0, 0),
                             align=TextNode.ACenter, scale = .15, mayChange = 1,
                             text="Level Done")
        self.levelEndText.hide()
        self.errorText = OnscreenText(
                             style=1, fg=(1,1,0,1), pos=(0, -0.65, 0),
                             align=TextNode.ACenter, scale = .1, mayChange = 1)
        self.errorText.hide()
        
        self.healthBarWidth = 0.8
        
        cardMaker = CardMaker("card maker")
        self.healthBar = render2d.attachNewNode(cardMaker.generate())
        self.healthBarBack = render2d.attachNewNode(cardMaker.generate())
        self.healthBar.setPos(-self.healthBarWidth/2.0, 0, -0.8)
        self.healthBarBack.setPos(-self.healthBarWidth/2.0-0.005, 0, -0.81)
        self.healthBar.setScale(self.healthBarWidth, 1, 0.1)
        self.healthBarBack.setScale(self.healthBarWidth+0.01, 1, 0.12)
        self.healthBar.setColorScale(0.2, 0.4, 1.0, 1)
        self.healthBarBack.setColorScale(0.2, 0.2, 0.2, 1)
        self.healthBar.setBin("fixed", 1)
        self.healthBarBack.setBin("fixed", 0)
        
        # The main game-loop
        self.updateTask = taskMgr.add(self.update, "main update task")
        self.updateTask.lastTime = 0
        
        # Miscellaneous game variables
        self.level = 0
        
        self.topWallZ = 2.5
        self.bottomWallZ = -2.5
        self.leftWallX = -3.0
        self.rightWallX = 3.0
        
        self.enemyModels = ["enemy1", "enemy2", "boss"]
        self.waveNumbers = [5, 8, 2]
        self.numLevels = len(self.enemyModels)
        self.enemyHealths = [1, 3, 50]
        self.enemyClasses = ["Enemy", "Enemy", "Boss"]
        
        self.enemies = []
        
        self.shots = []
        
        self.waves = []
        
        self.rootNode = render.attachNewNode(PandaNode("root"))
        
        self.waveTimer = 0
        self.levelEndTimer = 0
        
        self.playerAcceleration = 20.0
        self.player = self.makePlayer()
    
    def setKey(self, key, state):
        self.keys[key] = state
    
    # Game logic
    def update(self, task):
        if task.lastTime == 0:
            dt = 0
        else:
            dt = task.time - task.lastTime
        task.lastTime = task.time
        
        if self.player is None:
            return Task.cont
        
        if self.player.health <= 0:
            return Task.cont
        
        if self.levelEndTimer > 0:
            if self.level < self.numLevels:
                self.levelEndTimer -= dt
                self.updateLevelEndText()
                if self.levelEndTimer <= 0:
                    self.startNextLevel()
            return Task.cont
        
        if len(self.enemies) == 0:
            if len(self.waves) > 0:
                self.waveTimer -= dt
                if self.waveTimer <= 0:
                    self.waveTimer = WAVE_DELAY
                    numEnemies = self.waves.pop(0)
                    self.setWaveText()
                    enemyX = random.uniform(self.leftWallX*2.0/3.0, self.rightWallX*2.0/3.0)
                    enemyZ = self.topWallZ
                    for i in range(numEnemies):
                        enemy = self.makeEnemy(self.level)
                        enemy.manipulator.setPos(enemyX, 0, enemyZ+i*0.4)
                        enemy.waypoint = Vec3(enemyX,
                                              0,
                                              enemyZ+0.1)
                        self.enemies.append(enemy)
            elif len(self.shots) == 0:
                self.levelEndTimer = LEVEL_END_DURATION
                self.updateLevelEndText()
                self.levelEndText.show()
                return Task.cont
        
        if self.keys["up"]:
            self.player.velocity += Vec3(0, 0, self.playerAcceleration*dt)
        if self.keys["down"]:
            self.player.velocity += Vec3(0, 0, -self.playerAcceleration*dt)
        if self.keys["left"]:
            self.player.velocity += Vec3(-self.playerAcceleration*dt, 0, 0)
        if self.keys["right"]:
            self.player.velocity += Vec3(self.playerAcceleration*dt, 0, 0)
        if self.keys["fire"]:
            self.player.fireWeapon(self)
        
        self.player.update(self, dt)
        playerX = self.player.manipulator.getX()
        playerZ = self.player.manipulator.getZ()
        if playerZ < self.bottomWallZ+0.2:
            self.player.manipulator.setZ(self.bottomWallZ+0.2)
        elif playerZ > self.topWallZ-0.2:
            self.player.manipulator.setZ(self.topWallZ-0.2)
        if playerX < self.leftWallX:
            self.player.manipulator.setX(self.leftWallX)
        elif playerX > self.rightWallX:
            self.player.manipulator.setX(self.rightWallX)
        
        speed = self.player.velocity.length()
        frictionMagnitude = FRICTION*dt
        if speed > frictionMagnitude:
            friction = Vec3(-self.player.velocity)
            friction.normalize()
            friction *= frictionMagnitude
            self.player.velocity += friction
        else:
            self.player.velocity = Vec3(0, 0, 0)
        
        for obj in self.enemies:
            obj.update(self, dt)
            if obj.health <= 0:
                self.makeExplosion(obj.manipulator.getPos(), (1.0, 0.9, 0.3, 1), (1.0, 0.1, 0, 0), obj.explosionSize)
                obj.destroy()
        self.enemies = [x for x in self.enemies if x.health > 0]
        
        for shot in self.shots:
            shot.update(self, dt)
            if shot.id > 0:
                if shot.overlaps(self.player):
                    self.shotHits(shot, self.player)
            else:
                for obj in self.enemies:
                    if shot.overlaps(obj):
                        self.shotHits(shot, obj)
                        obj.scaleHealthRepresentation()
                        break
            if shot.health > 0:
                shotZ = shot.manipulator.getZ()
                shotX = shot.manipulator.getX()
                if shotZ > self.topWallZ or shotZ < self.bottomWallZ or \
                   shotX > self.rightWallX or shotX < self.leftWallX:
                    shot.health = -1
                    shot.destroy()
        self.shots = [x for x in self.shots if x.health > 0]
        
        healthBarScale = self.player.health*self.healthBarWidth/self.player.initialHealth
        if healthBarScale < 0:
            healthBarScale = 0
        self.healthBar.setSx(healthBarScale)
        
        if self.player.health <= 0:
            self.levelEndText["text"] = "You have died!"
            self.levelEndText.show()
            self.saveButton["state"] = DGG.DISABLED
            self.makeExplosion(self.player.manipulator.getPos(), (0.25, 0.5, 1.0, 1), (0.1, 0.3, 0.7, 1), self.player.explosionSize)
        
        return Task.cont
    
    def shotHits(self, shot, obj):
        obj.health -= shot.health
        shot.health = -1
        sequence = Sequence()
        scaleInterval = LerpScaleInterval(shot.manipulator, 0.2, Vec3(7.0, 1, 0.1), Vec3(1, 1, 1))
        destruction = Func(shot.destroy)
        sequence.append(scaleInterval)
        sequence.append(destruction)
        sequence.start()
    
    def makeExplosion(self, pos, startColour, endColour, size):
        parallel = Parallel()
        for i in range(5):
            explosion = loader.loadModel("surface")
            explosion.reparentTo(render)
            explosion.setPos(pos+Vec3(random.uniform(-size/8.0, size/8.0),
                                      0,
                                      random.uniform(-size/8.0, size/8.0)))
            #explosion.setR(random.uniform(0, 360))
            explosion.setTexture(loader.loadTexture("shot.png"))
            explosion.setTransparency(TransparencyAttrib.MAlpha)
            explosion.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            explosion.setDepthTest(False)
            explosion.setDepthWrite(False)
            explosion.setBin("unsorted", 0)
            explosion.setLightOff()
            innerParallel = Parallel()
            scaleInterval = LerpScaleInterval(explosion, random.uniform(0.35, 0.5),
                                                         random.uniform(size-0.07, size+0.13),
                                                         random.uniform(0.07, 0.12))
            startR = random.uniform(0, 360)
            endR = startR + random.uniform(-50, 50)
            rInterval = LerpHprInterval(explosion, random.uniform(0.35, 0.5),
                                                         (0, 0, endR),
                                                         (0, 0, startR))
            fadeInterval = LerpColorScaleInterval(explosion, 0.45, endColour, startColour)
            innerParallel.append(scaleInterval)
            innerParallel.append(rInterval)
            innerParallel.append(fadeInterval)
            destruction = Func(explosion.removeNode)
            sequence = Sequence()
            sequence.append(innerParallel)
            sequence.append(destruction)
            parallel.append(sequence)
        parallel.start()
    
    def makePlayer(self):
        obj = GameObject(80, -1, 0.15)
        obj.explosionSize = 1.0
        model = loader.loadModel("player")
        model.reparentTo(obj.manipulator)
        obj.manipulator.reparentTo(self.rootNode)
        obj.weapon = Weapon(1.0, 1, 1, (0.1, 0.3, 1.0, 1))
        obj.weaponMuzzle.setPos(0, 0, 0.2)
        playerLight = PointLight("player light")
        playerLight.setColor(Vec4(0.9, 0.95, 1.0, 1))
        playerLight.setAttenuation(Vec3(0, 0, 0.9))
        playerLightNodePath = obj.manipulator.attachNewNode(playerLight)
        playerLightNodePath.setPos(0, -1, 1)
        render.setLight(playerLightNodePath)
        return obj
    
    def makeEnemy(self, level):
        obj = eval(self.enemyClasses[level-1]+"(self.enemyHealths[level-1], self.enemyModels[level-1])")
        
        maxWeaponPoints = level*3+1
        for i in range(level):
            weaponPoints = maxWeaponPoints
            cooldown = 1.4
            numShots = 1
            damage = 1
            weaponPoints -= 3
            while weaponPoints > 0:
                attributeSelector = random.randint(0, 2)
                if attributeSelector == 0 and cooldown > 0.1:
                    cooldown -= 0.1
                elif attributeSelector == 1 and numShots < 7:
                    numShots += 1
                elif attributeSelector == 2:
                    damage *= 2.5
                weaponPoints -= 1
            shotColour = (damage/(maxWeaponPoints-3.0), 0.7, numShots/7.0, 1)
            weapon = Weapon(cooldown, numShots, damage, shotColour)
            obj.weaponList.append(weapon)
        
        obj.manipulator.reparentTo(self.rootNode)
        obj.weaponMuzzle.setPos(0, 0, -0.2)
        obj.weaponMuzzle.setR(180)
        return obj
    
    def cleanLevel(self):
        render.setLightOff()
        if self.rootNode is not None:
            self.rootNode.removeNode()
        self.rootNode = render.attachNewNode(PandaNode("root"))
        self.emptyLevel()
    
    def emptyLevel(self):
        for obj in self.enemies:
            obj.destroy()
        for obj in self.shots:
            obj.destroy()
        self.shots = []
        self.enemies = []
    
    def startNextLevel(self):
        
        self.level += 1
        self.emptyLevel()
        
        self.levelEndText.hide()
        
        self.setLevelText()
        
        attributeSelector = random.choice([0, 1])
        if attributeSelector == 0 and self.player.weapon.cooldown > 0.1:
            self.player.weapon.cooldown -= 0.4
        elif attributeSelector == 1 and self.player.weapon.numShots < 7:
            self.player.weapon.numShots += 1.5
        self.player.weapon.shotColour = (min(self.player.weapon.shotColour[0]+0.2, 1),
                                         min(self.player.weapon.shotColour[1]+0.4, 1),
                                         min(self.player.weapon.shotColour[2]+0.5, 1),
                                         1)
        
        self.waves = []
        for i in range(self.waveNumbers[self.level-1]-1):
            self.waves.append(random.randint(2, 2+i*2))
    
    def updateLevelEndText(self):
        self.levelEndText.show()
        if self.level == self.numLevels:
            self.levelEndText["text"] = "YOU WIN!"
        else:
            self.levelEndText["text"] = "Next Level Begins In:\n{0:.1f}".format(self.levelEndTimer)
    
    def setWaveText(self):
        self.waveText["text"] = "Waves left: "+str(len(self.waves))
    
    def setLevelText(self):
        self.levelText["text"] = "Level " + str(self.level)
    
    # Saving and loading!
    def save(self):
        try:
            GameSaver.saveGame(self, SAVE_GAME_FILE, False)
        except IOError:
            self.errorText.show()
            self.errorText["text"] = "Failed to save game!"
            taskMgr.doMethodLater(4, self.errorText.hide, "hide error", extraArgs=[])
    
    def load(self):
        # Reactivate the save button in case it was 
        # deactivated by the player dying
        self.saveButton["state"] = DGG.NORMAL
        
        try:
            result = GameSaver.loadGame(SAVE_GAME_FILE)
            self.loadFromSaveData(result, self)
        except IOError:
            self.errorText.show()
            self.errorText["text"] = "Failed to load game!"
            taskMgr.doMethodLater(4, self.errorText.hide, "hide error", extraArgs=[])
    
    ## Methods for the construction of types that are not
    ## simple types, but which do not derive from SaveableObject
    
    ### Vectors will simply be stored as tuples
    def getVectorForSave(self, vec):
        return (vec[0], vec[1], vec[2])
    
    def getVector2ForSave(self, vec):
        return (vec[0], vec[1])
    
    def getVector4ForSave(self, vec):
        return (vec[0], vec[1], vec[2], vec[3])
    
    def makeVectorFromSave(self, description):
        x = description.dataList[0].dataList[0]
        y = description.dataList[1].dataList[0]
        z = description.dataList[2].dataList[0]
        return Vec3(float(x), float(y), float(z))
    
    def makeVector2FromSave(self, description):
        x = description.dataList[0].dataList[0]
        y = description.dataList[1].dataList[0]
        return Vec2(float(x), float(y))
    
    def makeVector4FromSave(self, description):
        x = description.dataList[0].dataList[0]
        y = description.dataList[1].dataList[0]
        z = description.dataList[2].dataList[0]
        w = description.dataList[3].dataList[0]
        return Vec4(float(x), float(y), float(z), float(w))
    
    ## enemies will be identified by an id number
    def getGameObjectID(self, obj):
        return obj.id
    
    def getGameObjectFromSave(self, id):
        for obj in self.enemies:
            if obj.id == id:
                return obj
    
    ## These next two methods should be originally defined in SaveableObject;
    ##  we override them here to provide the specifics of loading
    ##  our game
    def loadFromSaveData(self, data, world):
        # Clean up our old data
        self.cleanLevel()
        self.player.destroy()
        self.player = None
        
        # Load the new data!
        SaveableObject.loadFromSaveData(self, data, world)
        
        self.setWaveText()
        self.setLevelText()
        self.levelEndText.hide()
    
    def getSaveData(self, forLevelSave):
        # I strongly recommend getting the GameSaveEntry object
        # that you work with from the parent class, even if that's
        # just SaveableObject. This allows the system the
        # opportunity to get save data defined in parent classes
        # and allows the SaveableObject class to perform
        # some initialisation
        # See the Enemy class for an example.
        result = SaveableObject.getSaveData(self, forLevelSave)
        
        result.addItem("waves = ", self.waves)
        result.addItem("waveTimer =", self.waveTimer)
        result.addItem("levelEndTimer = ", self.levelEndTimer)
        result.addItem("level = ", self.level)
        
        objEntry = GameSaveEntry()
        for obj in self.enemies:
            objEntry.addItem("", obj.getSaveData(forLevelSave))
        result.addItem("loadEnemies", objEntry)
        
        shotEntry = GameSaveEntry()
        for shot in self.shots:
            shotEntry.addItem("", shot.getSaveData(forLevelSave))
        result.addItem("loadShots", shotEntry)
        
        playerEntry = GameSaveEntry()
        playerEntry.addItem("", self.player.getSaveData(forLevelSave))
        result.addItem("loadPlayer", playerEntry)
        
        # Don't forget to return the result!
        return result
    
    def loadEnemies(self, data, world):
        for datum in data.dataList:
            # Since we have more than one enemy type, we use
            # GameSaveEntry's "objType" member to tell us what
            # class to instantiate. The code below presumes that
            # we've given our classes a method that creates an
            # object with "blank" data.

            # Since we only have a string identifying the type of Enemy in question,
            # we've set up a dictionary to associate class-names with actual class-objects.
            # See the bottom of the file for the implementation of this!
            #
            # Admittedly, with so few classes we could likely just use a set of if-else statements.
            # However, this should scale better to larger projects, I think.
            if datum.objType in gameObjectClassListing:
                newObj = gameObjectClassListing[datum.objType].makeBlankObject()
                newObj.loadFromSaveData(datum, self)
                newObj.manipulator.reparentTo(self.rootNode)
                newObj.scaleHealthRepresentation()
                self.enemies.append(newObj)
    
    def loadShots(self, data, world):
        for datum in data.dataList:
            newObj = Shot(0, 0, 0, world, None, (0, 0, 0, 0))
            newObj.loadFromSaveData(datum, self)
            self.shots.append(newObj)
    
    def loadPlayer(self, data, world):
        self.player = self.makePlayer()
        self.player.loadFromSaveData(data.dataList[0], self)

# Game classes
class Weapon(SaveableObject):
    def __init__(self, cooldown, numShots, damage, shotColour):
        self.cooldown = cooldown
        self.numShots = numShots
        self.damage = damage
        self.shotColour = shotColour
    
    # Since this class just holds simple data, we can probably leave out
    # the "loadFromSaveData" method and rely on the implementation in
    # SaveableObject
    
    def getSaveData(self, forLevelSave):
        result = SaveableObject.getSaveData(self, forLevelSave)
        
        result.addItem("cooldown =", self.cooldown)
        result.addItem("numShots =", self.numShots)
        result.addItem("damage =", self.damage)
        result.addItem("shotColour = ", self.shotColour)
        
        # Don't forget to return the result!
        return result
    
class GameObject(SaveableObject):
    def __init__(self, health, id, size):
        self.initialHealth = health
        self.health = health
        self.id = id
        self.size = size
        self.velocity = Vec3(0, 0, 0)
        self.manipulator = NodePath(PandaNode("manipulator"))
        self.weaponMuzzle = self.manipulator.attachNewNode(PandaNode("manipulator"))
        self.weaponCooldownTimer = 1
        self.weapon = None
        self.explosionSize = 1.0
        
        self.maxSpeed = 1.2
    
    # Saving and loading
    
    def getSaveData(self, forLevelSave):
        result = SaveableObject.getSaveData(self, forLevelSave)
        
        result.addItem("setPosFromSave", self.manipulator.getPos())
        result.addItem("initialHealth =", self.initialHealth)
        result.addItem("health =", self.health)
        result.addItem("id =", self.id)
        result.addItem("size =", self.size)
        result.addItem("velocity =", self.velocity)
        result.addItem("weaponCooldownTimer =", self.weaponCooldownTimer)
        if self.weapon is not None:
            # Placing the weapon's data into another GameSaveEntry
            # should prevent GameSaver from attempting to rebuild
            # the weapon itself, which, since GameSaver doesn't
            # include our classes, it presumably doesn't know how
            # to do. It does make for a minor nuisance in "loadWeapon",
            # however.
            weaponEntry = GameSaveEntry()
            weaponEntry.addItem("", self.weapon.getSaveData(forLevelSave))
            result.addItem("loadWeapon", weaponEntry)
        
        result.addItem("setWeaponMuzzle", (self.weaponMuzzle.getR(), self.weaponMuzzle.getPos()))
        
        # Don't forget to return the result!
        return result
    
    def setPosFromSave(self, data, world):
        self.manipulator.setPos(data)
    
    def setWeaponMuzzle(self, data, world):
        if len(data) < 2:
            return
        self.weaponMuzzle.setR(data[0])
        self.weaponMuzzle.setPos(data[1])
    
    def loadWeapon(self, data, world):
        weapon = Weapon(0, 0, 0, (0, 0, 0, 0))
        # Since, as mentioned in "getSaveData" just above,
        # we wrapped our weapon in a GameSaveEntry the
        # actual weapon data should be within the datalist
        # of the entry that we just got, rather than contained
        # in that entry itself. We first perform a safety check
        # against the possibility of an empty datalist being sent.
        if len(data.dataList) == 0:
            return
        weapon.loadFromSaveData(data.dataList[0], world)
        self.weapon = weapon
    
    ## Override this in sub-classes to get the appropriate sub-class
    @staticmethod
    def makeBlankObject():
        return GameObject(0, 0, 0)
    
    # Game logic
    def update(self, world, dt):
        if self.velocity.length() > self.maxSpeed:
            self.velocity.normalize()
            self.velocity *= self.maxSpeed
        
        self.manipulator.setPos(self.manipulator, self.velocity*dt)
        
        if self.weaponCooldownTimer > 0:
            self.weaponCooldownTimer -= dt
    
    def fireWeapon(self, world):
        if self.weapon is None:
            return
        if self.weaponCooldownTimer > 0:
            return
        
        angle = 0
        baseR = self.weaponMuzzle.getR()
        self.fireShot(world, self.weaponMuzzle, self.weapon.damage, self.weapon.shotColour)
        for i in range(int(self.weapon.numShots-1)*2):
            shotIndex = i+2
            self.weaponMuzzle.setR(baseR)
            sign = 1
            if i % 2 == 0:
                sign = -1
            self.weaponMuzzle.setR(self.weaponMuzzle, (shotIndex//2)*30*sign)
            self.fireShot(world, self.weaponMuzzle, self.weapon.damage, self.weapon.shotColour)
        self.weaponMuzzle.setR(baseR)
        self.weaponCooldownTimer = self.weapon.cooldown
    
    def fireShot(self, world, muzzleNP, shotDamage, shotColour):
        shot = Shot(shotDamage, self.id, 0.02, world, muzzleNP, shotColour)
        world.shots.append(shot)
    
    def overlaps(self, otherObj):
        x = self.manipulator.getX()
        z = self.manipulator.getZ()
        otherX = otherObj.manipulator.getX()
        otherZ = otherObj.manipulator.getZ()
        halfSize = self.size/2.0
        otherHalfSize = otherObj.size/2.0
        
        if x - halfSize > otherX + otherHalfSize:
            return False
        if x + halfSize < otherX - otherHalfSize:
            return False
        if z - halfSize > otherZ + otherHalfSize:
            return False
        if z + halfSize < otherZ - otherHalfSize:
            return False
        
        return True
    
    def destroy(self):
        self.manipulator.removeNode()

class Enemy(GameObject):
    def __init__(self, health, modelName):
        GameObject.__init__(self, health, 1, 0.25)
        self.waypoint = None
        self.weaponSwitchTimer = 0
        self.weaponList = []
        self.explosionSize = 0.7
        
        self.healthRepresentation = None
        
        self.modelName = ""
        self.loadModel(modelName)
    
    # Saving and loading
    def getSaveData(self, forLevelSave):
        # Since Enemy's parent class, GameObject, is a SaveableObject,
        # we probably want to call the version of "getSaveData" in
        # GameObject as well, so that the data defined there is also
        # saved for our enemy objects
        result = GameObject.getSaveData(self, forLevelSave)
        
        result.addItem("loadModel", self.modelName)
        result.addItem("waypoint =", self.waypoint)
        result.addItem("weaponSwitchTimer =", self.weaponSwitchTimer)
        weaponListEntry = GameSaveEntry()
        for weapon in self.weaponList:
            weaponListEntry.addItem("", weapon.getSaveData(forLevelSave))
        result.addItem("loadWeaponList", weaponListEntry)
        
        # Don't forget to return the result!
        return result
    
    def loadModel(self, modelName, world=None):
        if self.healthRepresentation is not None:
            self.healthRepresentation.removeNode()
            self.healthRepresentation = None
        self.modelName = modelName
        if len(modelName) > 0:
            model = loader.loadModel(modelName)
            model.reparentTo(self.manipulator)
            
            self.healthRepresentation = loader.loadModel("surface")
            self.healthRepresentation.setR(random.uniform(0, 360))
            self.healthRepresentation.setTexture(loader.loadTexture("enemyHealthCircle.png"))
            self.healthRepresentation.setTransparency(TransparencyAttrib.MAlpha)
            self.healthRepresentation.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            self.healthRepresentation.setDepthTest(False)
            self.healthRepresentation.setDepthWrite(False)
            self.healthRepresentation.setBin("unsorted", 0)
            self.healthRepresentation.reparentTo(model)
            self.scaleHealthRepresentation()
    
    def scaleHealthRepresentation(self):
        self.healthRepresentation.setScale(self.health*(self.size+0.3)/self.initialHealth)
    
    def loadWeaponList(self, data, world):
        self.weaponList = []
        for datum in data.dataList:
            weapon = Weapon(0, 0, 0, (0, 0, 0, 0))
            weapon.loadFromSaveData(datum, world)
            self.weaponList.append(weapon)
    
    ## Override this in sub-classes to get the appropriate sub-class
    @staticmethod
    def makeBlankObject():
        return Enemy(0, "")

    # Game logic
    def update(self, world, dt):
        # Head for the next waypoint
        if self.waypoint is not None:
            diff = self.waypoint - self.manipulator.getPos()
            if diff.lengthSquared() < 0.4:
                self.waypoint = Vec3(random.uniform(-1, 1),
                                     0,
                                     random.uniform(-1, 1))
            else:
                diff.y = 0
                diff.normalize()
                diff *= 0.5
                self.velocity += diff*dt
        
        if len(self.weaponList) > 0:
            self.weaponSwitchTimer -= dt
            if self.weaponSwitchTimer <= 0:
                self.weaponSwitchTimer = random.uniform(1.0, 2.0)
                self.weapon = random.choice(self.weaponList)
        
        self.fireWeapon(world)
        
        GameObject.update(self, world, dt)

# This class only really exists as an excuse to use the
# class-detection mechanism in "loadEnemies", above
class Boss(Enemy):
    def __init__(self, health, modelName):
        Enemy.__init__(self, health, modelName)
        self.size = 0.7
        self.maxSpeed = 0.9
        self.explosionSize = 1.5
    
    ## Override this in sub-classes to get the appropriate sub-class
    @staticmethod
    def makeBlankObject():
        return Boss(0)


class Shot(GameObject):
    def __init__(self, damage, id, size, world, muzzleNP, shotColour):
        GameObject.__init__(self, damage, id, size)
        
        self.maxSpeed = 3.2
        
        self.shotScalar = 3.0
        
        self.shotModel = loader.loadModel("surface")
        self.shotNP = self.manipulator.attachNewNode(PandaNode("intermediate node"))
        self.shotModel.reparentTo(self.shotNP)
        self.shotModel.setR(random.uniform(0.0, 360.0))
        if muzzleNP is not None:
            self.shotNP.setR(muzzleNP.getR(render))
        self.shotNP.setScale(0.1, 1, 0.1*self.shotScalar)
        self.shotNP.setTexture(loader.loadTexture("shot.png"))
        self.shotNP.setColorScale(shotColour)
        self.shotNP.setTransparency(TransparencyAttrib.MAlpha)
        self.shotNP.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
        self.shotNP.setDepthTest(False)
        self.shotNP.setDepthWrite(False)
        self.shotNP.setBin("unsorted", 0)
        self.shotNP.setLightOff()
        if muzzleNP is not None:
            self.manipulator.setPos(muzzleNP.getPos(render))
        self.manipulator.reparentTo(world.rootNode)
        if muzzleNP is not None:
            self.velocity = muzzleNP.getQuat(render).getUp()
            self.velocity *= self.maxSpeed
    
    def getSaveData(self, forLevelSave):
        # Since Shot's parent class, GameObject, is a SaveableObject,
        # we probably want to call the version of "getSaveData" in
        # GameObject as well, so that the data defined there is also
        # saved for our enemy objects
        result = GameObject.getSaveData(self, forLevelSave)
        
        result.addItem("setColour", self.shotNP.getColorScale())
        result.addItem("setShotOrientations", (self.shotNP.getR(), self.shotModel.getR()))
        
        # Don't forget to return the result!
        return result
    
    def setColour(self, data, world):
        self.shotNP.setColorScale(data)
    
    def setShotOrientations(self, data, world):
        self.shotNP.setR(data[0])
        self.shotModel.setR(data[1])
    
    def overlaps(self, otherObj):
        x = self.manipulator.getX()
        z = self.manipulator.getZ()
        otherX = otherObj.manipulator.getX()
        otherZ = otherObj.manipulator.getZ()
        halfSize = self.size/2.0
        otherHalfSize = otherObj.size/2.0
        
        if x - halfSize > otherX + otherHalfSize:
            return False
        if x + halfSize < otherX - otherHalfSize:
            return False
        if z - halfSize*self.shotScalar > otherZ + otherHalfSize:
            return False
        if z + halfSize*self.shotScalar < otherZ - otherHalfSize:
            return False
        
        return True

# A dictionary of classes known to the game, for use
# when determining subclassing
masterClassDict = {x[0] : x[1] for x in inspect.getmembers(sys.modules[__name__], inspect.isclass)}

# A dictionary of GameObject classes, for use when
# loading GameObjects. This is used in the "loadEnemies"
# method, above.
gameObjectClassListing = GameObject.__subclasses__()
gameObjectClassListing = {x.__name__ : x for x in gameObjectClassListing}
gameObjectClassListing[GameObject.__name__] = GameObject

game = Game()
run()