# -*- encoding: utf-8 -*-

import os, shutil, json
from typing import List, Optional
from pathlib import Path
from PyQt6.QtCore import QDir, QFileInfo, QDirIterator, QFile, QFileInfo, qDebug

import mobase # type: ignore

from ..basic_features import BasicGameSaveGameInfo, BasicLocalSavegames, BasicModDataChecker
from ..basic_game import BasicGame

from .baldursgate3 import ModSettingsHelper

class BaldursGate3Game(BasicGame, mobase.IPluginFileMapper):
    Name = "Baldur's Gate 3 Unofficial Support Plugin"
    Author = "chazwarp923 & Dragozino"
    Version = "2.4.5"

    GameName = "Baldur's Gate 3"
    GameShortName = "baldursgate3"
    GameNexusName = "baldursgate3"
    GameValidShortNames = ["baldursgate3"]
    GameNexusId = 3474
    GameSteamId = [1086940]
    GameGogId = [1456460669]
    GameBinary = "bin/bg3.exe"
    GameDataPath = "Data"
    GameSaveExtension = "lsv"
    GameDocumentsDirectory = (
        os.getenv("LOCALAPPDATA")
        + "/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/"
    )
    GameSavesDirectory = (
        os.getenv("LOCALAPPDATA")
        + "/Larian Studios/Baldur's Gate 3/PlayerProfiles/Public/Savegames/Story"
    )
    GameIniFiles = ["modsettings.lsx", "config.lsf", "profile8.lsf", "UILayout.lsx"]

    PAK_MOD_PREFIX = "PAK_FILES"
    SCRIPT_EXTENDER_CONFIG_PREFIX = "SE_CONFIG"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)

        self._register_feature(BasicGameSaveGameInfo(
            lambda s: s.with_suffix(".webp")
        ))

        self._register_feature(BaldursGate3ModDataChecker())

        self._register_feature(BasicLocalSavegames(self.savesDirectory()))
        
        self._organizer.modList().onModInstalled(self.onModInstalled)
        self._organizer.modList().onModRemoved(self.onModRemoved)

        self._organizer.onAboutToRun(self.onAboutToRun)
        self._organizer.onFinishedRun(self.onFinishedRun)
        
        self._organizer.onUserInterfaceInitialized(self.onUserInterfaceLoad)
        self._organizer.onProfileCreated(self.onProfileCreated)

        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "BG3 - Vulkan", QFileInfo(self.gameDirectory(), "bin/bg3.exe")
            ).withArgument("--skip-launcher"),
            mobase.ExecutableInfo(
                "BG3 - DX11", QFileInfo(self.gameDirectory(), "bin/bg3_dx11.exe")
            ).withArgument("--skip-launcher"),
            mobase.ExecutableInfo(
                "Larian Launcher",
                QFileInfo(self.gameDirectory(), "Launcher/LariLauncher.exe"),
            ),
        ]

    def mappings(self) -> List[mobase.Mapping]:
        map = []

        appdata_path = QDir(os.getenv("LOCALAPPDATA") + "/Larian Studios/Baldur's Gate 3/")
         
        modDirs = [self.PAK_MOD_PREFIX]
        self._listDirsRecursive(modDirs, prefix=self.PAK_MOD_PREFIX)
        for dir_ in modDirs:
            for file_ in self._organizer.findFiles(path=dir_, filter=lambda x: True):
                m = mobase.Mapping()
                m.createTarget = True
                m.isDirectory = False
                m.source = file_
                m.destination = os.path.join(
                    appdata_path.absoluteFilePath("Mods"),
                    file_.split(self.PAK_MOD_PREFIX)[1].strip("\\").strip("/"),
                )
                map.append(m)
        
        # configDirs = [self.SCRIPT_EXTENDER_CONFIG_PREFIX]
        # self._listDirsRecursive(configDirs, prefix=self.SCRIPT_EXTENDER_CONFIG_PREFIX)
        
        Path(QDir(os.getenv("LOCALAPPDATA") + "/Larian Studios/Baldur's Gate 3/").absoluteFilePath("Script Extender")).mkdir(parents=True, exist_ok=True)
        Path(QDir(os.getenv("LOCALAPPDATA") + "/Larian Studios/Baldur's Gate 3/").absoluteFilePath("Mods")).mkdir(parents=True, exist_ok=True)
        
        modList = self._organizer.modList()
        for mod in modList.allMods():
            if not (int(modList.state(mod) / 2) % 2 != 0):
                continue  # Skip disabled mods

            mod_source_path = modList.getMod(mod).absolutePath()
            se_config_path = os.path.join(mod_source_path, "SE_CONFIG")

            # Map the folders/files from SE_CONFIG in this mod
            for root, dirs, files in os.walk(mod_source_path):
                if "SE_CONFIG" in root:
                    # Calculate the relative path from SE_CONFIG
                    relative_path = os.path.relpath(root, se_config_path)

                    # Map directories
                    for dir_ in dirs:
                        m = mobase.Mapping()
                        m.createTarget = True
                        m.isDirectory = True
                        m.source = os.path.join(root, dir_)
                        m.destination = os.path.join(
                            QDir(os.getenv("LOCALAPPDATA") + "/Larian Studios/Baldur's Gate 3/").absoluteFilePath("Script Extender"),
                            relative_path,
                            dir_.strip("\\").strip("'/")
                        )
                        map.append(m)

                    # Map files
                    for file_ in files:
                        m = mobase.Mapping()
                        m.createTarget = True
                        m.isDirectory = False
                        m.source = os.path.join(root, file_)
                        m.destination = os.path.join(
                            QDir(os.getenv("LOCALAPPDATA") + "/Larian Studios/Baldur's Gate 3/").absoluteFilePath("Script Extender"),
                            relative_path,
                            file_.strip("\\").strip("'/")
                        )
                        map.append(m)
                        
        map.append(
            mobase.Mapping(
                source = self._organizer.profile().absolutePath() + "/modsettings.lsx",
                destination = self.GameDocumentsDirectory + "/modsettings.lsx",
                is_directory = False,
            )
        )
        
        return map

    def _listDirsRecursive(self, dirs_list, prefix=""):
        dirs = self._organizer.listDirectories(prefix)
        for dir_ in dirs:
            dir_ = os.path.join(prefix, dir_)
            dirs_list.append(dir_)
            self._listDirsRecursive(dirs_list, dir_)
            
    def onUserInterfaceLoad(self, window) -> None:
        profile = self._organizer.profile()
        profilePath = profile.absolutePath()
        mods_cache_path = os.path.join(profilePath, "modsCache.json")
        
        if not os.path.exists(mods_cache_path):
            with open(mods_cache_path, 'w') as file:
                    json.dump({}, file)
        return True
    
    def onProfileCreated(self, profile) -> None:
        profilePath = profile.absolutePath()
        mods_cache_path = os.path.join(profilePath, "modsCache.json")
        
        if not os.path.exists(mods_cache_path):
            with open(mods_cache_path, 'w') as file:
                    json.dump({}, file)
        return True

    def onModInstalled(self, mod) -> bool:
        ModSettingsHelper.modInstalled(self._organizer.modList(), self._organizer.profile(), mod.name())    
        return True
    
    def onModRemoved(self, mod) -> bool:
        ModSettingsHelper.modRemoved(self._organizer.modList(), self._organizer.profile(), mod)
        return True

    def onAboutToRun(self, mod):
        ModSettingsHelper.generateSettings(self._organizer.modList(), self._organizer.profile())
        return True

    def onFinishedRun(self, path: str, integer: int) -> bool:
        seDir = os.path.join(os.getenv("LOCALAPPDATA"), "Larian Studios", "Baldur's Gate 3", "Script Extender")
        mo2_se_config_dir = os.path.join(self._organizer.overwritePath(), "SE_CONFIG")

        if not os.path.isdir(seDir): return True
        
        configDirs = [seDir]
        
        self._listDirsRecursive(configDirs, prefix=seDir)

        for dir_ in configDirs:
            if os.path.exists(dir_):
                for file_ in os.listdir(dir_):
                    full_src_path = os.path.join(dir_, file_)
                    
                    if os.path.isdir(full_src_path):
                        # Construct destination path keeping only the last part of the directory
                        dest_path = os.path.join(mo2_se_config_dir, os.path.basename(full_src_path))

                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)

                        # Move all contents of the directory
                        for root, subdirs, files in os.walk(full_src_path):
                            for file_ in files:
                                file_src = os.path.join(root, file_)
                                file_dest = os.path.join(dest_path, os.path.relpath(file_src, full_src_path))  # Maintain structure
                                file_dest_dir = os.path.dirname(file_dest)
                                
                                if not os.path.exists(file_dest_dir):
                                    os.makedirs(file_dest_dir)

                                shutil.move(file_src, file_dest)

                        # Remove the source directory after moving its contents
                        shutil.rmtree(full_src_path)

                    elif os.path.isfile(full_src_path):
                        # For files, move directly under the target folder
                        dest_path = os.path.join(mo2_se_config_dir, os.path.basename(dir_))  # Keep only the last part of dir_

                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)

                        shutil.move(full_src_path, os.path.join(dest_path, file_))

                # Remove the current directory after processing all files and subdirectories
                if os.path.isdir(dir_):
                    os.rmdir(dir_)
        
        return True

class BaldursGate3ModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        folders: List[mobase.IFileTree] = []
        files: List[mobase.FileTreeEntry] = []
        for entry in tree:
            if isinstance(entry, mobase.IFileTree):
                folders.append(entry)
            else:
                files.append(entry)

        VALID_FOLDERS = [
            "Cursors",
            "DLC",
            "Engine",
            "Fonts",
            "Generated",
            "Localization",
            "Mods",
            "PakInfo",
            "PlayerProfiles",
            "Public",
            "Root",
            "Shaders",
            "Video",
            BaldursGate3Game.PAK_MOD_PREFIX,
            BaldursGate3Game.SCRIPT_EXTENDER_CONFIG_PREFIX,
        ]

        VALID_FILE_EXTENSIONS = [
            ".pak",
            ".dll",
            ".json"
        ]

        for mainFolder in folders:
            for validFolder in VALID_FOLDERS:
                if mainFolder.name().lower() == validFolder.lower():
                    return mobase.ModDataChecker.VALID

        for mainFile in files:
            for extension in VALID_FILE_EXTENSIONS:
                if mainFile.name().lower().endswith(extension.lower()) and mainFile.name() != "info.json":
                    return mobase.ModDataChecker.FIXABLE
                
        for mainFolder in folders:
            if mainFolder.name().lower() == "bin":
                return mobase.ModDataChecker.FIXABLE
            else:
                for mainFile in mainFolder:
                    for extension in VALID_FILE_EXTENSIONS:
                            if mainFile.name().lower().endswith(extension.lower()) and mainFile.name() != "info.json":
                                return mobase.ModDataChecker.FIXABLE
                
        for src_folder in folders:
            for dst_folder in VALID_FOLDERS:
                if src_folder.name().lower() == dst_folder.lower():
                    return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        folders: List[mobase.IFileTree] = []
        files: List[mobase.FileTreeEntry] = []
        for entry in tree:
            if isinstance(entry, mobase.IFileTree):
                folders.append(entry)
            else:
                files.append(entry)

        REMOVE_FILES = [
            "readme",
            "info.json"
        ]
        REMOVE_FILE_EXTENSIONS = [
            ".url",
            ".html",
            ".ink"
        ]

        # Remove unnecessary files
        for mainFile in files:
            for extension in REMOVE_FILE_EXTENSIONS:
                if mainFile.name().lower().endswith(extension.lower()):
                     tree.remove(mainFile)
            for filename in REMOVE_FILES:
                if mainFile.name().lower() == filename:
                     tree.remove(mainFile)

            
        for mainFolder in folders:
            for mainFile in mainFolder:
                for extension in REMOVE_FILE_EXTENSIONS:
                    if mainFile.name().lower().endswith(extension.lower()):
                        tree.remove(mainFolder)
                for filename in REMOVE_FILES:
                    if mainFile.name().lower() == filename:
                       tree.remove(mainFolder)


        for mainFile in files:
            if mainFile.name().lower().endswith(".pak".lower()):
                if mainFile is None: continue
                tree.move(mainFile, "/PAK_FILES/", policy=mobase.IFileTree.MERGE)
            if mainFile.name().lower().endswith(".json".lower()) and mainFile.name() != "info.json":
                tree.move(mainFile, "/SE_CONFIG/", policy=mobase.IFileTree.MERGE)
                    
        for mainFolder in folders:
            if mainFolder.name().lower() == "bin":
                tree.move(mainFolder, "/Root/", policy=mobase.IFileTree.MERGE)
            else:
                for mainFile in mainFolder:
                    if mainFile is None: continue
                    if mainFile.name().lower().endswith(".pak".lower()):
                        tree.move(mainFile, "/PAK_FILES/", policy=mobase.IFileTree.MERGE)
                    if mainFile.name().lower().endswith(".json".lower()) and mainFile.name() != "info.json":
                        tree.move(mainFile, "/SE_CONFIG/", policy=mobase.IFileTree.MERGE)

        return tree
