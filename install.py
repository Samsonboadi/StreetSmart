import subprocess
import sys
import os
import pkg_resources
from qgis.core import (QgsVectorLayer,QgsExpressionContextUtils, QgsProject,Qgis,QgsApplication)  # pylint: disable=import-error
import re
from platform import python_version

def install_cefpython3():
    python_V = python_version().split('.')
    python_V = 'Python'+str(python_V[0])+str(python_V[1])
    Qgispython_path =os.path.join(os.path.split(QgsApplication.prefixPath())[0],python_V) 

    qgis_python_path = os.path.join(Qgispython_path,'python') # Get the path to the QGIS Python interpreter
    site_packages = os.path.join(Qgispython_path,'Lib','site-packages')


    cefpython_install_command = [
        qgis_python_path, "-m", "pip", "install", "Cefpython3", "--target",site_packages 
    ]

  
    try:
        subprocess.check_call(cefpython_install_command)
    #except subprocess Exception
    except subprocess.CalledProcessError as e:
        pass



def check_Cefpython_installation():

    # Check if Cefpython3 is installed
    cefpython_installed = False
    try:
        pkg_resources.get_distribution('cefpython3')
        cefpython_installed = True
    except pkg_resources.DistributionNotFound:
        pass

    if cefpython_installed:
        print("Cefpython3 is installed.")
    else:
        print("Cefpython3 is not installed.")
    
    return cefpython_installed




def copy_missen_DLLS(source_path, destination_path):
    """Copy missing dll's from Qgis bin directory into QGIS DLL folder."""

    # Copy files with administrative privileges
    try:
        subprocess.run(['cmd', '/c', 'copy', source_path, destination_path], shell=True, check=True)
        print("Files copied successfully with administrative privileges.")
    except subprocess.CalledProcessError as e:
        print("Error occurred while copying files:", e)






def is_valid_file_path(file_path):
    return os.path.exists(file_path)




def get_Qgis_Version():
    #Get Qgis version and append Ebinoath to system ENV
    get_Qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    Qgis_major_minor_version = get_Qgis_version.split('-')[0] #major plus minor release

    split_path = Qgis_major_minor_version.rsplit(".", 1) 
    Qgis_major_Version = split_path[0].strip("'") # major Release

    print("Qgis_major_minor_version",Qgis_major_minor_version)  # Output: C:\\Program Files\\QGIS 3.16
    print("Qgis_major_Version",Qgis_major_Version)  # Output: 15
    
    return [Qgis_major_minor_version, Qgis_major_Version]




def extract_python_Version():

    python_version = sys.version

    # Extract the Python version using regular expressions
    match = re.search(r'(\d+\.\d+\.\d+)', python_version)

    python_version = match.group(1)
    # Split the version string
    major, minor, _ = python_version.split(".")

    # Concatenate the major and minor version numbers
    converted_version = f"Python{major}{minor}"
    
    return converted_version




def check_DLLS():

    qgis_versions = get_Qgis_Version()

    destination_path_major_minor = os.path.join("C:\\Program Files\\QGIS " + qgis_versions[1], "apps", extract_python_Version(), "DLLs")
    destination_path_major = os.path.join("C:\\Program Files\\QGIS " + qgis_versions[0], "apps", extract_python_Version(), "DLLs")

    files = ['libssl-1_1-x64.dll', 'libcrypto-1_1-x64.dll']
    #destination_path_major_minor = os.path.join("C:\\Program Files\\QGIS " + qgis_versions[1], "apps", "Python37", "DLLs")
    
    if is_valid_file_path(destination_path_major_minor):
        # Check if the files exist at the specified path
        file_exists = all(os.path.exists(os.path.join(destination_path_major_minor, file)) for file in files)
        file_exists =[file_exists,destination_path_major_minor]
    else:
        file_exists = all(os.path.exists(os.path.join(destination_path_major, file)) for file in files)
        file_exists =[file_exists,destination_path_major]
    
    if file_exists[0]:
        print("Both files exist at the specified path.")
    else:
        print("One or both files do not exist at the specified path.")

    return file_exists




def return_Qgis_bin_path(path):
    # Split the path
    split_path = path.split("apps")[0]
    bin_path = os.path.join(split_path,"bin")
    return bin_path




        


    
    
    




    
    
    
    
    
    




    

    

   
 

    


