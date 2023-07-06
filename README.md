# Azure Netapp Files simplified in Ansible

This project is for all users of azure netapp files who like to deploy and automize their environment using ansible.
<br><br>
The first script "anf_volume.py" provides an easy way of deploying and maintaining volumes by limiting the required informations and automizes / abstracts the whole Netapp Account & Capacity Pool handling.<br><br>
<b>Features:</b><br>
<div><ul>
  <li>check if netapp account exists, and create one if missing</li>
  <li>check if capacity pool exists, and create one if missing (min 4 TB or given vol size if larger 4 TB)</li>
  <li>check if vol already exists, if yes extend or shrink, If not create</li>
  <li>adjust capacity pool, if volumes growth changes or new requires more space (shrink/grow)</li>
  <li>delete snapshots if existing before vol deletion</li>
  <li>delete volume, capacity pool, netapp account (only if it was the last vol and last capacity pool triggering deletion)</li>
  <li>volume state "offline" decreases the volume size to the minimum possible (used) capacity in the volume. for example: 1000 gb volume with only 200 gb used capacity will be decreased to 200 gb only.</li>
</ul></div>

<br><br>
<b>Parameters</b>

<b>Example</b>
<pre><code>
- name: "Azure - deploy/resize/update Azure NetApp Files volume"
  anf_volume:    
    provider: "azure"
    tenant: "00000000-0000-0000-0000-000000000000"
    subscription_id: "00000000-0000-0000-0000-000000000000"
    client_id: "00000000-0000-0000-0000-000000000000"
    secret: "my_app_secret"
    resource_group: "myanfrg"
    resource_group_net: "mynetrg"
    virtualnetwork: "vnet01"
    subnet: "anfsubnet"
    accountname: "myanfacc"
    location: "westeurope"
    sku: "Standard" 
    volname: "myvolume01"
    volsize: "500"    
    state: present
  delegate_to: localhost
</code></pre>
The second script "anf_volume_backup.py" provides easy anf snapshot management
