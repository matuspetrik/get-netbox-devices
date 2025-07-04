# Get Netbox Devices
An application to pull data from Netbox based o provided criteria.

Only os environment variables need to be edited to reflect the real status.

## Usage (Option #1)
```
git clone git@127.0.0.1:itdanucem/get-netbox-devices.git
cd get-netbox-devices
python -m venv venv
. venv/bin/activate
pip install -r requirementes.txt
export NETBOX_IPV4=10.52.1.49
export NETBOX_FQDN=svk-rnk-netbox.hdb.int
export NETBOX_TOKEN_RO=6f65de4dba8b5e13de52b91c119b2086a016bbd1
export NETBOX_TOKEN_RW=NONE
export OUTPUT_FILE_PATH=/home/itdanucem/ansible/inventory/hostfile.yml
python main.py
```

## Usage (Option #2)
### Write systemd service script to run the application
```
sudo cat > /etc/systemd/system/my-get-netbox-devices-for-ansible.service << EOF
[Unit]
Description=Ansible script to pull config from network devices and store on Gitea

[Service]
Type=simple
WorkingDirectory=/home/itdanucem/get-netbox-devices
User=itdanucem
Group=itdanucem
Environment=PATH=venv:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment="VIRTUAL_ENV=/home/itdanucem/get-netbox-devices/venv"
Environment=NETBOX_FQDN=svk-rnk-netbox.hdb.int
Environment=NETBOX_IPV4=10.52.1.49
Environment=NETBOX_TOKEN_RO=6f65de4dba8b5e13de52b91c119b2086a016bbd1
Environment=NETBOX_TOKEN_RW=TBD
Environment=OUTPUT_FILE_PATH=/home/itdanucem/ansible/inventory/hostfile.yml
ExecStart=/bin/bash -c 'source $VIRTUAL_ENV/bin/activate && python /home/itdanucem/get-netbox-devices/main.py'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```
### Then run the service:
```
systemctl restart my-get-netbox-devices-for-ansible.service
```
### You can also set a timer to run automatically at given time:
```
sudo cat > /etc/systemd/system/my-get-netbox-devices-for-ansible.timer <<EOF
[Unit]
Description=Run my-get-netbox-devices-for-ansible.service every night before actual backup run

[Timer]
# each day at given time
OnCalendar=*-*-* 03:10:00
Unit=my-get-netbox-devices-for-ansible.service

[Install]
WantedBy=timers.target
EOF
```
After altering systemd files don't forget to run
```
systemctl daemon-reload
```
command.