import urllib.request
import requests
import zipfile
import os
import subprocess


if not os.path.isfile("cvdump.exe"):
    print("Downloading cvdump")
    urllib.request.urlretrieve("https://github.com/microsoft/microsoft-pdb/raw/master/cvdump/cvdump.exe", "cvdump.exe")

def run_command(command):
    subprocess.run(command, shell=True, check=True)

def download_and_unzip(url, target_path):
    # Download the file
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to download file")

    # Write the downloaded content to a zip file
    zip_file_path = os.path.join(target_path, "downloaded.zip")
    with open(zip_file_path, "wb") as file:
        file.write(response.content)

    # Unzip the file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(target_path)

    print(f"File downloaded and extracted to {target_path}")

try:
    if not os.path.isdir('vcpkg'):
        print("vcpkg not found, dowloading")
        run_command("git clone https://github.com/Microsoft/vcpkg.git")
        run_command(".\\vcpkg\\bootstrap-vcpkg.bat")
        run_command(".\\vcpkg\\vcpkg integrate install")
        #for me this stuff only succeed in at least 10 tries 
        while True:
            try:
                run_command(".\\vcpkg\\vcpkg install protobuf protobuf:x64-windows")
                break
            except:
                print("install protobuf failed, retrying")
                continue
        
    if not os.path.isdir('protoc'):
        print("protoc not found, dowloading")
        os.makedirs("protoc", exist_ok=True)
        download_and_unzip("https://github.com/protocolbuffers/protobuf/releases/download/v21.12/protoc-21.12-win64.zip", "protoc")

    print("generating proto buf")
    run_command("protoc\\bin\\protoc.exe -I . --cpp_out=. --proto_path=. .\\protobufs.proto")

    os.makedirs("build", exist_ok=True)
    os.chdir("build")

    print("start compiling")
    run_command("cmake .. -DCMAKE_TOOLCHAIN_FILE=./vcpkg/scripts/buildsystems/vcpkg.cmake")
    run_command("cmake --build .")

    os.chdir("..")

    print("start dumping")
    run_command("python dumper.py")

    print("done")
except Exception as e:
    print(f"An error occurred: {e}")