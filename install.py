import subprocess
import sys
import os
import pkg_resources
from qgis.core import (QgsVectorLayer,QgsExpressionContextUtils, QgsProject,Qgis,QgsApplication)  # pylint: disable=import-error
import re
from platform import python_version
import shutil


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



def install_python_package(packagename):
    python_exe = os.path.join(sys.base_exec_prefix, "python.exe")
    command = [python_exe, "-m", "pip", "install", packagename, "-y"]
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        print("Cefpython3 was uninstalled successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall Cefpython3: {e}")
        print(e.stderr)


def uninstall_cefpython():
    python_exe = os.path.join(sys.base_exec_prefix, "python.exe")
    command = [python_exe, "-m", "pip", "uninstall", "cefpython3", "-y"]
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        print("Cefpython3 was uninstalled successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall Cefpython3: {e}")
        print(e.stderr)


def check_Cefpython_installation():
    cefpython_installed = False

    try:
        dist = pkg_resources.get_distribution('cefpython3')
        
        if dist.version == '66.1':
            print("Cefpython3 version 66.1 is installed, which is not supported.")
            # Since version 66.1 is not supported, attempt to uninstall it
            uninstall_cefpython()
        else:
            # If Cefpython3 is installed and not version 66.1, mark it as installed
            cefpython_installed = True
            print(f"Cefpython3 is installed with version {dist.version}, which is supported.")
    except pkg_resources.DistributionNotFound:
        print("Cefpython3 is not installed.")

    # Return the installation status of Cefpython3 (False if uninstalled or not installed, True otherwise)
    return cefpython_installed



def configure_paths():
    """Configures the environment to include the QGIS bin directory."""
    # Retrieve the QGIS version and split to get the main version part
    qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    qgis_version = qgis_version.split('-')[0]

    # Construct the source path dynamically
    qgis_bin_path = os.path.join(r"C:\Program Files\QGIS", qgis_version, "bin")

    # Append the constructed path to the system's PATH environment variable
    # It's often a safer choice to prepend (add in front) your path so it's searched first
    os.environ['PATH'] = qgis_bin_path + os.pathsep + os.environ['PATH']

    # Append the path to sys.path for Python to recognize it
    sys.path.append(qgis_bin_path)


def check_qgis_version():
    min_version = "3.20"
    max_version = "3.40"
    
    # Convert the version strings to tuples of integers for comparison
    min_version_tuple = tuple(map(int, min_version.split('.')))
    max_version_tuple = tuple(map(int, max_version.split('.')))
    current_version_tuple = tuple(map(int, Qgis.QGIS_VERSION.split('-')[0].split('.')))
    print(min_version_tuple)
    print(max_version_tuple)
    print(current_version_tuple)
    # Check if the current QGIS version falls within the min and max bounds
    if current_version_tuple < min_version_tuple or current_version_tuple > max_version_tuple:
        return False  # Not supported
    return True  # Supported




'''def copy_missen_DLLS(source_path, destination_path):
    """Copy missing dll's from Qgis bin directory into QGIS DLL folder."""

    # Copy files with administrative privileges
    try:
        subprocess.run(['cmd', '/c', 'copy', source_path, destination_path], shell=True, check=True)
        print("Files copied successfully with administrative privileges.")
    except subprocess.CalledProcessError as e:
        print("Error occurred while copying files:", e)'''


def copy_missen_DLLS(source, destination):
    try:
        shutil.copy(source, destination)
        print(f"Successfully copied {source} to {destination}")
    except IOError as e:
        print(f"Error occurred while copying {source}: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")



def is_valid_file_path(file_path):
    return os.path.exists(file_path)


def get_Qgis_Version():
    # Get QGIS version from the global scope
    get_Qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    Qgis_major_minor_version = get_Qgis_version.split('-')[0]  # Major plus minor release
    print("Full QGIS version:", get_Qgis_version)
    
    split_path = Qgis_major_minor_version.rsplit(".", 1)
    Qgis_major_Version = split_path[0].strip("'")  # Major Release
    
    print("QGIS Major-Minor version:", Qgis_major_minor_version)
    print("QGIS Major version:", Qgis_major_Version)

    # Get the installation directory of QGIS
    Qgis_install_dir = QgsApplication.prefixPath()
    print("QGIS Installation Directory:", Qgis_install_dir)

    # Extract the generic installation directory up to "QGIS"
    base_install_dir = Qgis_install_dir
    while not base_install_dir.endswith("QGIS"):
        base_install_dir = os.path.dirname(base_install_dir)
        if os.path.basename(base_install_dir).startswith("QGIS"):
            break

    print("Base QGIS Installation Directory:", base_install_dir)

    return [Qgis_major_minor_version, Qgis_major_Version, base_install_dir]



'''def get_Qgis_Version():
    #Get Qgis version and append Ebinoath to system ENV
    get_Qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    Qgis_major_minor_version = get_Qgis_version.split('-')[0] #major plus minor release

    split_path = Qgis_major_minor_version.rsplit(".", 1) 
    Qgis_major_Version = split_path[0].strip("'") # major Release

    print("Qgis_major_minor_version",Qgis_major_minor_version)  # Output: C:\\Program Files\\QGIS 3.16
    print("Qgis_major_Version",Qgis_major_Version)  # Output: 15
    
    return [Qgis_major_minor_version, Qgis_major_Version]'''




def extract_python_Version():

    #python_version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
    (major, minor) = sys.version_info.major, sys.version_info.minor
    # Extract the Python version using regular expressions
    #match = re.search(r'(\d+\.\d+\.\d+)', python_version)
    
    return major, minor



def is_valid_file_path(path):
    # Check if the directory exists
    return os.path.exists(path)

def check_DLLs():
    qgis_versions = get_Qgis_Version()
    Qgis_base_path = qgis_versions[2]  # Get the base path from the version information
    major, minor = extract_python_Version()  # Assuming this returns a string like "3.12"
    python_version = f"Python{major}{minor}"

    python_folder = os.path.join("apps", python_version, "DLLs")
    
    # Create paths to check for DLLs
    paths = [os.path.join(Qgis_base_path, python_folder)]
    #print("Qgis_base_path",Qgis_base_path)
    #print("python_folder",python_folder)
    # Conditional list of files based on the Python version
    files = []
    if (major, minor) < (3, 12):
        # Include specific DLLs for Python versions below 3.12
        files.extend(['libssl-1_1-x64.dll', 'libcrypto-1_1-x64.dll'])
    else:
        # Include specific DLLs for Python 3.12 and above
        files.extend(['libcrypto-3-x64.dll', 'libssl-3-x64.dll'])

    for path in paths:
        #print("Paths1",path)
        if is_valid_file_path(path):
            #print("Paths2",path)
            missing_files = [file for file in files if not os.path.exists(os.path.join(path, file))]
            print("missen files",missing_files)
            if not missing_files:
                print(f"All required DLLs are present in {path}.")
                return (False, path, None)  # No files are missing
            else:
                print(f"Missing {len(missing_files)} files in {path}: {', '.join(missing_files)}")
                return (True, path, missing_files)  # Return missing files as well

    print("No valid paths found for DLL checks.")
    return (True, path, files)


def return_Qgis_bin_path(path):
    # Split the path
    split_path = path.split("apps")[0]
    bin_path = os.path.join(split_path,"bin")
    return bin_path




        


    
    
    




    
    
    
    
    
    




    

    

   
 

    


