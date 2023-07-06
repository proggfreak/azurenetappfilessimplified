# Azure Netapp Files simplified in Ansible

This project is for all users of azure netapp files who like to deploy and automize their environment using ansible.
<br><br>
It provides an easy way of deploying and maintaining volumes by limiting the required informations and outomizes / abstracts the whole Netapp Account & Capacity Pool handling.
<br><br>
<b>Parameters</b>

<b>Example</b>
<pre><code>
- name: "Azure - deploy/resize/update Azure NetApp Files volume"
  anf_volume:    
    provider: "azure"
    tenant: "{{ cfgself.credentials.tenant_id }}"
    subscription_id: "{{ cfgself.credentials.subscription_id }}"
    client_id: "{{ cfgself.credentials.client_id }}"
    secret: "{{ cfgself.credentials.secret }}"
    resource_group: "{{ cfgself.rsg }}"
    resource_group_net: "{{ cfgself.network.rsg }}"
    virtualnetwork: "{{ cfgself.network.spoke }}"
    subnet: "{{ cfgself.network.subnet }}"
    accountname: "myanfacc"
    location: "westeurope"
    sku: "Standard" 
    volname: "myvolume01"
    volsize: "500"    
    state: present
  delegate_to: localhost
</code></pre>
