# Azure Netapp Files simplified in Ansible

This project is for all users of azure netapp files who like to deploy and automize their environment using ansible.
<br><br>
It provides an easy way of deploying and maintaining volumes by limiting the required informations and automizes / abstracts the whole Netapp Account & Capacity Pool handling.
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
