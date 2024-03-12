import os
import shutil
import hashlib
import subprocess
import sys
import time

# Constants and Globals
TEMP_DIR = '/tmp/optical-test'
ISO_NAME = 'optical-test.iso'
SAMPLE_FILE_PATH = '/usr/share/example-content/'
SAMPLE_FILE = 'Ubuntu_Free_Culture_Showcase'
MD5SUM_FILE = 'optical_test.md5'
START_DIR = os.getcwd()


def create_working_dirs():
    # First, create the temp dir and cd there
    print("Creating Temp directory and moving there ...")
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.chdir(TEMP_DIR)
    print(f"Now working in {os.getcwd()} ...")


def get_sample_data():
    # Get our sample files
    print(f"Getting sample files from {SAMPLE_FILE_PATH} ...")
    shutil.copy2(os.path.join(SAMPLE_FILE_PATH, SAMPLE_FILE), TEMP_DIR)


def generate_md5():
    # Generate the md5sum
    print("Generating md5sums of sample files ...")
    cur_dir = os.getcwd()
    os.chdir(SAMPLE_FILE)
    with open(MD5SUM_FILE, 'w') as md5file:
        for fname in os.listdir('.'):
            with open(fname, 'rb') as f:
                md5file.write(f"{hashlib.md5(f.read()).hexdigest()}  {fname}\n")
    os.chdir(cur_dir)
    check_md5(os.path.join(TEMP_DIR, MD5SUM_FILE))


def check_md5(file_path):
    print("Checking md5sums ...")
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.split()
            md5, file_name = parts[0], ' '.join(parts[1:])
            with open(file_name, 'rb') as file_to_check:
                data = file_to_check.read()
                calculated_md5 = hashlib.md5(data).hexdigest()
                if calculated_md5 != md5:
                    return False
    return True


def generate_iso():
    print("Creating ISO Image ...")
    subprocess.run(['genisoimage', '-input-charset', 'UTF-8', '-r', '-J', '-o', ISO_NAME, SAMPLE_FILE], check=True)


def burn_iso():
    print("Sleeping 10 seconds in case drive is not yet ready ...")
    time.sleep(10)
    print("Beginning image burn ...")
    if OPTICAL_TYPE == 'cd':
        subprocess.run(['wodim', '-eject', 'dev=' + OPTICAL_DRIVE, ISO_NAME], check=True)
    elif OPTICAL_TYPE in ['dvd', 'bd']:
        subprocess.run(['growisofs', '-dvd-compat', '-Z', OPTICAL_DRIVE + '=' + ISO_NAME], check=True)
    else:
        raise ValueError(f"Invalid type specified '{OPTICAL_TYPE}'")


def check_disk():
    timeout = 300
    sleep_count = 0
    interval = 3
    print("Waiting up to 5 minutes for drive to be mounted ...")
    while sleep_count < timeout:
        time.sleep(interval)
        sleep_count += interval
        try:
            subprocess.run(['mount', OPTICAL_DRIVE], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Drive appears to be mounted now")
            break
        except subprocess.CalledProcessError:
            pass

        if sleep_count >= timeout:
            print("WARNING: timeout Exceeded and no mount detected!")
            break

    mount_pt = os.path.join(TEMP_DIR, 'mnt')
    os.makedirs(mount_pt, exist_ok=True)
    subprocess.run(['mount', OPTICAL_DRIVE, mount_pt], check=True)
    for file in os.listdir(mount_pt):
        shutil.copy2(os.path.join(mount_pt, file), TEMP_DIR)
    return check_md5(MD5SUM_FILE)


def cleanup():
    print("Moving back to original location")
    os.chdir(START_DIR)
    print(f"Now residing in {os.getcwd()}")
    print("Cleaning up ...")
    subprocess.run(['umount', OPTICAL_DRIVE], check=True)
    shutil.rmtree(TEMP_DIR)
    subprocess.run(['eject', OPTICAL_DRIVE], check=True)


def failed(message):
    print(message)
    print("Attempting to clean up ...")
    cleanup()
    sys.exit(1)


OPTICAL_DRIVE = os.path.realpath(sys.argv[1]) if len(sys.argv) >= 2 else '/dev/sr0'
OPTICAL_TYPE = sys.argv[2] if len(sys.argv) > 3 else 'cd'

try:
    create_working_dirs()
    get_sample_data()
    if not generate_md5():
        raise Exception("Failed to generate initial md5")
    generate_iso()
    burn_iso()
    if not check_disk():
        raise Exception("Failed to verify files on optical disk")
    cleanup()
except Exception as e:
    failed(str(e))
