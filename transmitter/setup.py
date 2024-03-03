import paramiko

default_host = "raspi.local"
default_username = "raspi"

server = input("Enter the server hostname (default={}): ".format(default_host)).strip() or default_host
username = input("Enter username (default={}): ".format(default_username)).strip() or default_username
password = input("Enter password: ")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(server, username=username, password=password)
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("ls")

print(ssh_stdout.read().decode())
print(ssh_stderr.read().decode())
