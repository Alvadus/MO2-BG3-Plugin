# -*- encoding: utf-8 -*-

import mobase # type: ignore
import os
import platform
import json
import subprocess
from pathlib import Path
import shutil
from xml.dom import minidom
import xml.etree.ElementTree as ET
from PyQt6.QtCore import QDir, QFileInfo, QDirIterator, QFile, QFileInfo, qDebug

script_dir = os.path.abspath(__file__)

root_folder = Path(__file__).parents[4]

divine_path = os.path.join(Path(script_dir).parent, 'tools', 'Divine.exe')

def find_meta_lsx(name, path): # Find meta.lsx in directory
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

def extract_meta_lsx(pak_path, output_dir): # Extract meta.lsx from .pak file

    command = [
        str(divine_path),
        "-a", "extract-package",
        "-g", "bg3",
        "-s", str(pak_path),
        "-d", str(output_dir),
        "-x", "*/meta.lsx",
        "-l", "off"
    ]

    result = subprocess.run(
        command,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    modinfo = {
                "Name": "Override_Mod",
                "UUID": "Override_Mod",
                "Folder": "Override_Mod",
                "Version": "Override_Mod",
                "MD5": "Override_Mod"
            }

    if result.returncode == 0:
        meta_lsx_path = find_meta_lsx('meta.lsx', output_dir)

        if meta_lsx_path:
            modinfo = parse_meta_lsx(meta_lsx_path)
          
    return modinfo

   

def get_attribute_value(node, attr_id): # Extract attribute value
    attribute = node.find(f".//attribute[@id='{attr_id}']")
    return attribute.get('value') if attribute is not None else None

def get_attribute(info, *keys): # Match json attributes
    for key in keys:
        if key in info:
            return info[key]
    return None

def long_path_support(path):
    if platform.system() == 'Windows' and len(path) > 255:
        return f"\\\\?\\{os.path.abspath(path)}"
    return path

def parse_meta_lsx(meta_lsx_path): # Extract information from meta.lsx
    meta_lsx_path = long_path_support(meta_lsx_path)
    
    if not os.path.exists(meta_lsx_path):
        raise FileNotFoundError(f"The file {meta_lsx_path} does not exist.")
    
    if meta_lsx_path:
        tree = ET.parse(str(meta_lsx_path))
        root = tree.getroot()
        module_info = root.find(".//node[@id='ModuleInfo']")
        
        if module_info is None:
            raise ValueError(f"'ModuleInfo' node not found in {meta_lsx_path}. Check the XML structure.")
    
        mod_info = {
            'Folder': get_attribute_value(module_info, 'Folder'),
            'Name': get_attribute_value(module_info, 'Name'),
            'PublishHandle': get_attribute_value(module_info, 'PublishHandle'),
            'UUID': get_attribute_value(module_info, 'UUID'),
            'MD5': get_attribute_value(module_info, 'MD5'),
            'Version': get_attribute_value(module_info, 'Version64'),
        }
        return mod_info
    

def getModInfoFromCache(modName:str, profile: mobase.IProfile):
    profilePath = profile.absolutePath()
    cacheJsonPath = os.path.join(profilePath, "modsCache.json")
    
    if not os.path.exists(cacheJsonPath):
        print("modsCache.json not found.")
        return None
    
    with open(cacheJsonPath, 'r') as file:
        modsCache = json.load(file)
    
    # Return all .pak files related to the modName
    modPakFiles = []
    for pak_file, mod_info in modsCache.items():
        if "ModName" in mod_info and modName in mod_info["ModName"]:
            modPakFiles.append({pak_file: mod_info})
    
    if modPakFiles:
        return modPakFiles
    else:
        print(f"Mod '{modName}' not found in modsCache.json.")
        return None
    
def getModCachesFromName(modName: str, profile: mobase.IProfile):
    profilePath = profile.absolutePath()
    cacheJsonPath = os.path.join(profilePath, "modsCache.json")
    
    if not os.path.exists(cacheJsonPath):
        print("modsCache.json not found.")
        return None
    
    with open(cacheJsonPath, 'r') as file:
        modsCache = json.load(file)
        
    matchingMods = []
    for pak_file, mod_info in modsCache.items():
        if "ModName" in mod_info and modName in mod_info["ModName"]:
            matchingMods.append({pak_file: mod_info})
            # matchingMods[pak_file] = mod_info
        
    if matchingMods:
        return matchingMods
    else:
        print(f"Mod '{modName}' not found in modsCache.json.")
        return {}
    
def modInstalled(modList: mobase.IModList, profile: mobase.IProfile, mod) -> bool:
    modsCache = {}
    pakFileFolder = modList.getMod(mod).absolutePath() + "\\PAK_FILES"
    
    temp_dir = os.path.join(Path(__file__).resolve().parent, 'temp_extracted')
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if os.path.isdir(pakFileFolder):
        files = os.listdir(pakFileFolder)
        files = [f for f in files if f.lower().endswith(".pak")]
        for file in files:
            if file.endswith(".pak"):
                mod_temp_dir = os.path.join(temp_dir, file)
                if not os.path.exists(mod_temp_dir):
                    os.makedirs(mod_temp_dir)

                mod_info = extract_meta_lsx(os.path.join(pakFileFolder, file), mod_temp_dir)
                if mod_info:
                    modsCache[file] = mod_info
                    if "ModName" not in modsCache[file]:
                        modsCache[file]["ModName"] = []
                    if mod not in modsCache[file]["ModName"]:
                        modsCache[file]["ModName"].append(mod)
                    # modsCache[file]["ModName"] = mod
                    
    if modsCache:
        profilePath = profile.absolutePath()
        cacheJsonPath = os.path.join(profilePath, "modsCache.json")
        
        with open(cacheJsonPath, 'r') as file:
            cacheJson = json.load(file)
            
        for pak_file, mod_info in modsCache.items():
            if pak_file not in cacheJson:
                cacheJson[pak_file] = mod_info
            if pak_file in cacheJson:
                if mod not in cacheJson[pak_file]["ModName"]:
                    cacheJson[pak_file]["ModName"].append(mod)

        with open(cacheJsonPath, 'w') as file:
            json.dump(cacheJson, file, indent=4)
            
    # shutil.rmtree(temp_dir, ignore_errors=True)
    
    return cacheJson[pak_file] if modsCache else None
    
def fixModsCache(modList: mobase.IModList, profile: mobase.IProfile):
    profilePath = profile.absolutePath()
    cacheJsonPath = os.path.join(profilePath, "modsCache.json")
    
    with open(cacheJsonPath, 'r') as file:
        modsCache = json.load(file)
        
    if modsCache:
        for pak_file, mod_info in modsCache.items():
            for modName in mod_info["ModName"]:
                mod = modList.getMod(modName)
                if not mod:
                    modsCache[pak_file]["ModName"].remove(modName)
                    
        with open(cacheJsonPath, 'w') as file:
            json.dump(modsCache, file, indent=4)
       
def modRemoved(modList: mobase.IModList, profile: mobase.IProfile, modName: str) -> bool:
    profilePath = profile.absolutePath()
    cacheJsonPath = os.path.join(profilePath, "modsCache.json")
  
    with open(cacheJsonPath, 'r') as file:
        modsCache = json.load(file)
        
    matchingCache = getModCachesFromName(modName, profile)   
    if matchingCache:
        print("Mods found using", modName, ":", matchingCache)
        for match in matchingCache:    
            for pak_file, mod_info in match.items():
                if modName in modsCache[pak_file]["ModName"]:
                    modsCache[pak_file]["ModName"].remove(modName)
                if not modsCache[pak_file]["ModName"]:
                    del modsCache[pak_file]
                            
        with open(cacheJsonPath, 'w') as file:
            json.dump(modsCache, file, indent=4)
    else:
        print("No mods found using", modName)
        
def generateSettings(modList: mobase.IModList, profile: mobase.IProfile) -> bool:
    fixModsCache(modList, profile)
    
    modInfoDict = {}
    modSequence = modList.allModsByProfilePriority()
    
    temp_dir = os.path.join(Path(__file__).resolve().parent, 'temp_extracted')
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for mod in modSequence:
        if (int(modList.state(mod) / 2) % 2 != 0):  # Check if mod is active
            
            # Get all .pak files associated with the mod
            pak_files_info = getModInfoFromCache(mod, profile)
            if pak_files_info:
                modInfoDict[mod] = pak_files_info
            else:
                modInfoDict[mod] = modInstalled(modList, profile, mod)
                            
    root = minidom.Document()
    save = root.createElement('save')
    root.appendChild(save)
    version = root.createElement('version')
    version.setAttribute('major', '4')
    version.setAttribute('minor', '7')
    version.setAttribute('revision', '1')
    version.setAttribute('build', '3')
    save.appendChild(version)
    region = root.createElement('region')
    region.setAttribute('id', 'ModuleSettings')
    save.appendChild(region)
    nodeRoot = root.createElement('node')
    nodeRoot.setAttribute('id', 'root')
    region.appendChild(nodeRoot)
    nodeRootChildren = root.createElement('children')#the base element ModOrder and Mods nodes get appended to
    nodeRoot.appendChild(nodeRootChildren)

    nodeModOrder = root.createElement('node')
    nodeModOrder.setAttribute('id', 'ModOrder')
    nodeRootChildren.appendChild(nodeModOrder)
    nodeModOrderChildren = root.createElement('children')#the base element all "ModOrder" "Module" tags get appended to
    nodeModOrder.appendChild(nodeModOrderChildren)
    nodeModuleGustav = root.createElement('node')
    nodeModuleGustav.setAttribute('id', 'Module')
    nodeModOrderChildren.appendChild(nodeModuleGustav)
    attributeModOrderUUIDGustav = root.createElement('attribute')
    attributeModOrderUUIDGustav.setAttribute('id', 'UUID')
    attributeModOrderUUIDGustav.setAttribute('value', '28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8')
    attributeModOrderUUIDGustav.setAttribute('type', 'FixedString')
    nodeModuleGustav.appendChild(attributeModOrderUUIDGustav)

    nodeMods = root.createElement('node')
    nodeMods.setAttribute('id', 'Mods')
    nodeRootChildren.appendChild(nodeMods)
    nodeModsChildren = root.createElement('children')#the base element all "Mods" "ModuleShortDesc" tags get appended to
    nodeMods.appendChild(nodeModsChildren)
    nodeModuleShortDescGustav = root.createElement('node')
    nodeModuleShortDescGustav.setAttribute('id', 'ModuleShortDesc')
    nodeModsChildren.appendChild(nodeModuleShortDescGustav)
    attributeFolderGustav = root.createElement('attribute')
    attributeFolderGustav.setAttribute('id', 'Folder')
    attributeFolderGustav.setAttribute('value', 'GustavDev')
    attributeFolderGustav.setAttribute('type', 'LSString')
    nodeModuleShortDescGustav.appendChild(attributeFolderGustav)
    attributeMD5Gustav = root.createElement('attribute')
    attributeMD5Gustav.setAttribute('id', 'MD5')
    attributeMD5Gustav.setAttribute('value', '5e66b6872b07a6b2283a4e4a9cccb325')
    attributeMD5Gustav.setAttribute('type', 'LSString')
    nodeModuleShortDescGustav.appendChild(attributeMD5Gustav)
    attributeNameGustav = root.createElement('attribute')
    attributeNameGustav.setAttribute('id', 'Name')
    attributeNameGustav.setAttribute('value', 'GustavDev')
    attributeNameGustav.setAttribute('type', 'LSString')
    nodeModuleShortDescGustav.appendChild(attributeNameGustav)
    attributeModsUUIDGustav = root.createElement('attribute')
    attributeModsUUIDGustav.setAttribute('id', 'UUID') 
    attributeModsUUIDGustav.setAttribute('value', '28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8')
    attributeModsUUIDGustav.setAttribute('type', 'FixedString')
    nodeModuleShortDescGustav.appendChild(attributeModsUUIDGustav)
    attributeVersion64Gustav = root.createElement('attribute')
    attributeVersion64Gustav.setAttribute('id', 'Version64') 
    attributeVersion64Gustav.setAttribute('value', '144961545746289842')
    attributeVersion64Gustav.setAttribute('type', 'int64')
    nodeModuleShortDescGustav.appendChild(attributeVersion64Gustav)   
    
    # Geneate modsettings.lsx LoadOrder
    for mod, pak_files_info_list in modInfoDict.items():
        if not pak_files_info_list:
            continue
        
        for pak_info_dict in pak_files_info_list:
            if isinstance(pak_info_dict, dict):
                for pak_file, mod_info in pak_info_dict.items():
                    name = mod_info.get('Name')
                    folder = mod_info.get('Folder')
                    uuid = mod_info.get('UUID')
                    version = mod_info.get('Version')

                    # Add to ModOrder
                    nodeModule = root.createElement('node')
                    nodeModule.setAttribute('id', 'Module')
                    nodeModOrderChildren.appendChild(nodeModule)
                    attributeModOrderUUID = root.createElement('attribute')
                    attributeModOrderUUID.setAttribute('id', 'UUID')
                    attributeModOrderUUID.setAttribute('value', uuid)
                    attributeModOrderUUID.setAttribute('type', 'FixedString')
                    nodeModule.appendChild(attributeModOrderUUID)
                    nodeModOrderChildren.appendChild(nodeModule)

                    nodeModuleShortDesc = root.createElement('node')
                    nodeModuleShortDesc.setAttribute('id', 'ModuleShortDesc')
                    nodeModsChildren.appendChild(nodeModuleShortDesc)
                    attributeFolder = root.createElement('attribute')
                    attributeFolder.setAttribute('id', 'Folder')
                    attributeFolder.setAttribute('value', folder)
                    attributeFolder.setAttribute('type', 'LSString')
                    nodeModuleShortDesc.appendChild(attributeFolder)
                    attributeMD5 = root.createElement('attribute')
                    attributeMD5.setAttribute('id', 'MD5')
                    attributeMD5.setAttribute('value', '')
                    attributeMD5.setAttribute('type', 'LSString')
                    nodeModuleShortDesc.appendChild(attributeMD5)
                    attributeName = root.createElement('attribute')
                    attributeName.setAttribute('id', 'Name')
                    attributeName.setAttribute('value', name)
                    attributeName.setAttribute('type', 'LSString')
                    nodeModuleShortDesc.appendChild(attributeName)
                    attributeModsUUID = root.createElement('attribute')
                    attributeModsUUID.setAttribute('id', 'UUID')
                    attributeModsUUID.setAttribute('value', uuid)
                    attributeModsUUID.setAttribute('type', 'FixedString')
                    nodeModuleShortDesc.appendChild(attributeModsUUID)
                    attributeVersion = root.createElement('attribute')
                    attributeVersion.setAttribute('id', 'Version64')
                    attributeVersion.setAttribute('value', version)
                    attributeVersion.setAttribute('type', 'int64')
                    nodeModuleShortDesc.appendChild(attributeVersion)
                    nodeModsChildren.appendChild(nodeModuleShortDesc)

    # Save the modsettings.lsx file
    xml_str = root.toprettyxml(indent="  ")
    outputPath = profile.absolutePath() + "\\modsettings.lsx"
    with open(outputPath, "w", encoding='utf-8') as f:
        f.write(xml_str)
        f.close()

    # Clean up the temp directory
    temp_dir = Path(temp_dir)
    if os.path.exists(temp_dir):
        for item in temp_dir.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                print(f"Error deleting {item}: {e}")

    return True