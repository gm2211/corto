import paramiko


def run(ssh_connection, command):
    stdin, stdout, stderr = ssh_connection.exec_command(command)
    print(stdout.read().decode())
    print(stderr.read().decode())


# noinspection PyBroadException
def mkdir_corto(ssh_connection):
    sftp = ssh_connection.open_sftp()
    try:
        sftp.mkdir("~/projects/corto/lora")
    except Exception:
        pass
    try:
        sftp.mkdir("~/projects/corto")
    except Exception:
        pass
    sftp.close()


default_host = "raspi.local"
default_username = "raspi"

server = input("Enter the server hostname (default={}): ".format(default_host)).strip() or default_host
username = input("Enter username (default={}): ".format(default_username)).strip() or default_username
password = input("Enter password: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(server, username=username, password=password)

run(ssh, "sudo apt-get update")
run(ssh, "sudo apt-get upgrade -y")
run(ssh, "sudo apt-get install python3-pip -y")
run(ssh, "curl https://pyenv.run | bash")
run(ssh, "echo 'export PYENV_ROOT=\"$HOME/.pyenv\"' >> ~/.zshrc")
run(ssh, "echo 'command -v pyenv >/dev/null || export PATH=\"$PYENV_ROOT/bin:$PATH\"' >> ~/.zshrc")
run(ssh, "echo 'eval \"$(pyenv init -)\"' >> ~/.zshrc")
run(ssh, "pyenv install 3.11.8")
run(ssh, "pyenv virtualenv 3.11.8 corto")
run(ssh, "pyenv activate corto")
run(ssh, "pip3 install --upgrade adafruit-blinka")
run(ssh, "python3 -m pip install inventorhatmin")
run(ssh, "sudo raspi-config nonint do_i2c 0")
run(ssh, "pip3 install adafruit-circuitpython-busdevice")
run(ssh, "pip3 install adafruit-circuitpython-ssd1306")
run(ssh, "pip3 install adafruit-circuitpython-rfm9x")
run(ssh, "pip3 install --upgrade adafruit-python-shell click")
run(ssh, "sudo -E env PATH=$PATH python3 raspi-spi-reassign.py --ce0=disabled --ce1=disabled")
print("If you still running into ce0 and ce1 issues, try running the following command:")
print("sudo -E env PATH=$PATH python3 raspi-spi-reassign.py --ce0=5 --ce1=6")
run(ssh, "sudo raspi-config nonint do_i2c 0 ")

mkdir_corto(ssh)

with open("font5x8.bin", "rb") as file:
    sftp = ssh.open_sftp()
    sftp.putfo(file, "~/projects/corto/lora/font5x8.bin")
    sftp.close()

with open("raspi-spi-reassign.py", "r") as file:
    sftp = ssh.open_sftp()
    sftp.putfo(file, "~/projects/corto/lora/raspi-spi-reassign.py")
    sftp.close()
