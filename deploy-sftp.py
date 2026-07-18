#!/usr/bin/env python3
"""
ZICORE SFTP Deployer — preserves UTF-8 encoding.
Usage: py deploy-sftp.py [--files file1 file2 ...] [--all-html] [--all] [--py] [--css-js]
"""
import paramiko
import sys
import os
import glob

SERVER = '192.168.1.85'
USER = 'z'
LOCAL_ROOT = os.path.dirname(os.path.abspath(__file__))
REMOTE_ROOT = '/opt/zicore-materializer'

# Files to deploy
DEPLOY_MAP = {}

# Add frontend HTML files
for f in glob.glob(os.path.join(LOCAL_ROOT, 'frontend', '*.html')):
    name = os.path.basename(f)
    DEPLOY_MAP[f'frontend/{name}'] = f

# Add CSS/JS
for f in glob.glob(os.path.join(LOCAL_ROOT, 'frontend', 'css', '*.css')):
    name = os.path.basename(f)
    DEPLOY_MAP[f'frontend/css/{name}'] = f
for f in glob.glob(os.path.join(LOCAL_ROOT, 'frontend', 'js', '*.js')):
    name = os.path.basename(f)
    DEPLOY_MAP[f'frontend/js/{name}'] = f

# Add zicore Python modules
for f in glob.glob(os.path.join(LOCAL_ROOT, 'zicore', '*.py')):
    name = os.path.basename(f)
    DEPLOY_MAP[f'zicore/{name}'] = f

# Add web_server.py
DEPLOY_MAP['web_server.py'] = os.path.join(LOCAL_ROOT, 'web_server.py')

# Add data files
for root, dirs, files in os.walk(os.path.join(LOCAL_ROOT, 'frontend', 'data')):
    for name in files:
        full = os.path.join(root, name)
        rel = 'frontend/data/' + os.path.relpath(full, os.path.join(LOCAL_ROOT, 'frontend', 'data')).replace('\\', '/')
        DEPLOY_MAP[rel] = full

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER)
    return ssh

def deploy(ssh, files_to_deploy):
    sftp = ssh.open_sftp()
    uploaded = 0
    skipped = 0
    errors = []

    for remote_rel, local_path in files_to_deploy:
        if not os.path.exists(local_path):
            continue
        remote_path = f'{REMOTE_ROOT}/{remote_rel}'
        tmp_path = f'/tmp/zicore-deploy/{remote_rel}'
        try:
            # Ensure remote dirs exist
            remote_dir = os.path.dirname(remote_path).replace('\\', '/')
            tmp_dir = os.path.dirname(tmp_path).replace('\\', '/')
            ssh.exec_command(f'mkdir -p {tmp_dir}')
            import time; time.sleep(0.05)

            # Upload to /tmp, then sudo cp
            sftp.put(local_path, tmp_path)
            stdin, stdout, stderr =             ssh.exec_command(f'sudo cp {tmp_path} {remote_path}')
            stdout.read()
            err = stderr.read().decode().strip()
            if err and 'Permission denied' not in err:
                errors.append(f'{remote_rel}: {err}')
                skipped += 1
            else:
                uploaded += 1
        except Exception as e:
            errors.append(f'{remote_rel}: {e}')
            skipped += 1

    sftp.close()
    return uploaded, skipped, errors

def main():
    args = sys.argv[1:]
    ssh = connect()

    if not args:
        # Deploy everything
        files = list(DEPLOY_MAP.items())
        print(f'Deploying {len(files)} files via SFTP...')
    elif '--py' in args:
        files = [(k, v) for k, v in DEPLOY_MAP.items() if k.endswith('.py')]
        print(f'Deploying {len(files)} Python files...')
    elif '--css-js' in args:
        files = [(k, v) for k, v in DEPLOY_MAP.items() if k.endswith('.css') or k.endswith('.js')]
        print(f'Deploying {len(files)} CSS/JS files...')
    elif '--files' in args:
        idx = args.index('--files')
        target_files = args[idx+1:]
        files = [(k, v) for k, v in DEPLOY_MAP.items() if any(t in k for t in target_files)]
        print(f'Deploying {len(files)} matching files...')
    else:
        files = list(DEPLOY_MAP.items())
        print(f'Deploying {len(files)} files via SFTP...')

    uploaded, skipped, errors = deploy(ssh, files)
    print(f'Uploaded: {uploaded}')
    if skipped:
        print(f'Skipped: {skipped}')
        for e in errors:
            print(f'  ERROR: {e}')

    ssh.close()
    print('Done.')

if __name__ == '__main__':
    main()
