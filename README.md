# Azure Netapp Files simplified in Ansible

This project is for all users of azure netapp files who like to deploy and automize their environment using ansible.
<br><br>
## anf_volume.py
The first script provides an easy way of deploying and maintaining volumes by limiting the required informations and automizes / abstracts the whole Netapp Account & Capacity Pool handling.<br><br>
<b>Features:</b><br>
<div><ul>
  <li>check if netapp account exists, and create one if missing</li>
  <li>check if capacity pool exists, and create one if missing (min 4 TB or given vol size if larger 4 TB)</li>
  <li>check if vol already exists, if yes extend or shrink, If not create</li>
  <li>efficient capacity pool handling: new volume created or existing updated requires more space / existing volume deleted or shrinked results in possible capacity pool shrink (shrink/grow)</li>
  <li>delete snapshots if existing before vol deletion</li>
  <li>delete volume, capacity pool, netapp account (only if it was the last vol and last capacity pool triggering deletion)</li>
  <li>volume state "offline" decreases the volume size to the minimum possible (used) capacity in the volume. for example: 1000 gb volume with only 200 gb used capacity will be decreased to 200 gb only.</li>
</ul></div>

<br><br>
<b>Parameters</b>
<table>
  <tr>
    <th>parameter</th>
    <th>requred</th>
    <th>default</th>
    <th>possible values</th>
    <th>description</th>
  </tr>
  <tr>
    <td>provider</td>
    <td>no</td>
    <td>azure</td>
    <td>azure</td>
    <td>only azure support right now.</td>
  </tr>
  <tr>
    <td>tenant</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>azure tenenat id</td>
  </tr>
  <tr>
    <td>subscription_id</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>azure subscription id</td>
  </tr>
  <tr>
    <td>client_id</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>application (client) id</td>
  </tr>
  <tr>
    <td>secret</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>application (client) secret</td>
  </tr>
  <tr>
    <td>resource_group</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>resource group for your anf service</td>
  </tr>
  <tr>
    <td>resource_group_net</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>resource group of the existing anf vnet/subnet</td>
  </tr>
  <tr>
    <td>virtualnetwork</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>vnet for anf</td>
  </tr>
  <tr>
    <td>subnet</td>
    <td>no</td>
    <td>sto</td>
    <td></td>
    <td>subnet for anf. Till now only basic networking supported. Requirements can be found here: <link>https://learn.microsoft.com/en-us/azure/azure-netapp-files/azure-netapp-files-network-topologies#subnets</link></td>
  </tr>
  <tr>
    <td>accountname</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>name of the netapp account</td>
  </tr>
  <tr>
    <td>location</td>
    <td>no</td>
    <td>westeurope</td>
    <td></td>
    <td>all available anf locations. check out: <link>https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/?products=netapp</link></td>
  </tr>
  <tr>
    <td>sku</td>
    <td>no</td>
    <td>Standard</td>
    <td>Standard<br>Premium<br>Ultra</td>
    <td>Storage Class of the volume. sku info can be found here: <link>https://learn.microsoft.com/en-us/azure/azure-netapp-files/azure-netapp-files-service-levels</link></td>
  </tr>
  <tr>
    <td>volname</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>name of the volume</td>
  </tr>
  <tr>
    <td>volsize</td>
    <td>yes</td>
    <td></td>
    <td></td>
    <td>volume size in gb</td>
  </tr>
  <tr>
    <td>state</td>
    <td>no</td>
    <td>present</td>
    <td>present<br>absent<br>offline</td>
    <td>"present" creates or updates a volume and if required the netapp account and capacity pool.<br><br>"absent" deletes a volume and if it's the last one deletes the capacity pool and storage account.<br><br>"offline" shrinks the volume to the minimum possible used space.</td>
  </tr>
</table>

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

## anf_volume_backup.py
The second script provides easy anf snapshot management
