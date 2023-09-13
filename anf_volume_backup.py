#!/usr/bin/python

DOCUMENTATION = '''
---
module: anf_volume_backup
short_description: Backup (snap) and Restore (snap restore) of Volumes.
Creator: Christian Gruetzner
Created: 2019-08-13

Updated: 2022-07-14 - Add native ANF backup feature to store files on BLOB
					  https://docs.microsoft.com/en-us/azure/azure-netapp-files/backup-introduction

API Version support: (Get-AzResourceProvider -ProviderNamespace Microsoft.NetApp).ResourceTypes

2022-01-01
'''

from ansible.module_utils.basic import *
import requests
import json
import time
import datetime



def setup(data):

	capacitypool = data['sku'].lower()

	if data['provider'] == "azure":
		#get first access to azure api and the correct tenant/subscription
		api_url = "https://login.microsoftonline.com/"+data['tenant']+"/oauth2/token"
		body = "grant_type=client_credentials&client_id="+data['client_id']+"&client_secret="+data['secret']+"&resource=https://management.core.windows.net"
		headers = {
			'content-type': 'application/x-www-form-urlencoded'
		}
		token = requests.get(api_url, data=body, headers=headers)
		meta = {token.status_code}

		if token.status_code == 200:

			tokeninfo = token.json()
			
			if tokeninfo.get('token_type') == "Bearer":

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ list snap policies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				#https://docs.microsoft.com/en-us/rest/api/netapp/snapshot-policies/list?tabs=HTTP
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies?api-version=2021-10-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				has_changed = False
				is_failed = False
				meta = {"nothing done."}

				primarypolicyname = "primary"+str(data["retention_days"])+"d"

				found_primary5d = 0
				found_primarycustpolicy = 0

				for policy in returndata["value"]:
					if "primary5d" in policy["name"]:
						found_primary5d = 1
					if primarypolicyname in policy["name"]:
						found_primarycustpolicy = 1

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ if no snap policy "primary5d" exist, create one ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				if found_primary5d == 0:
					#create snapshot policy
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies/primary5d?api-version=2021-10-01"

					body_raw = {
						'location': data['location'],
						'properties': {
							'enabled': 'true',
							'dailySchedule': {
								'hour': '23',
								'minute': '12',
								'snapshotsToKeep': '5'
							},
							'hourlySchedule': {
								'minute': '',
								'snapshotsToKeep': ''
							},
							'monthlySchedule': {
								'daysOfMonth': '',
								'hour': '',
								'minute': '',
								'snapshotsToKeep': ''
							},
							'weeklySchedule': {
								'day': '',
								'hour': '',
								'minute': '',
								'snapshotsToKeep': ''
							},
						}
					}
					body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 201:
						has_changed = True
						is_failed = False
						meta = {"snapshot policy primary5d created."}
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ if no snap policy "primary30d" exist, create one ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				if found_primarycustpolicy == 0:
					#create snapshot policy
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies/"+primarypolicyname+"?api-version=2021-10-01"

					body_raw = {
						'location': data['location'],
						'properties': {
							'enabled': 'true',
							'dailySchedule': {
								'hour': '23',
								'minute': '12',
								'snapshotsToKeep': data["retention_days"]
							},
							'hourlySchedule': {
								'minute': '',
								'snapshotsToKeep': ''
							},
							'monthlySchedule': {
								'daysOfMonth': '',
								'hour': '',
								'minute': '',
								'snapshotsToKeep': ''
							},
							'weeklySchedule': {
								'day': '',
								'hour': '',
								'minute': '',
								'snapshotsToKeep': ''
							},
						}
					}
					body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 201:
						has_changed = True
						is_failed = False
						meta = {"snapshot policy "+primarypolicyname+" created."}
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ list backup policies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				#https://docs.microsoft.com/en-us/rest/api/netapp/backup-policies/list?tabs=HTTP
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/backupPolicies?api-version=2021-10-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				#file = open ("/tmp/testfile.txt","w")
				#file.write (httpreturn.text)
				#file.write (returndata["error"]["code"])
				#file.write (str(httpreturn.status_code))
				#file.close()

				has_changed = False
				is_failed = False
				meta = {"nothing done."}

				if data["retention_days"]:
					backuppolicyname = "backup"+str(data["retention_days"])+"d"
				else:
					backuppolicyname = "backup30d"	#default if not defined
				
				found_backuppolicy = 0

				for policy in returndata["value"]:
					if backuppolicyname in policy["name"]:
						found_backuppolicy = 1

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ if no backup policy with retention name exist, create one ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				if found_backuppolicy == 0:
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/backupPolicies/"+backuppolicyname+"?api-version=2021-10-01"

					body_raw = {
						'location': data['location'],
						'properties': {
							'enabled': 'true',
							'dailyBackupsToKeep': data["retention_days"],
							'weeklyBackupsToKeep': '0',
							'monthlyBackupsToKeep': '0',
						}
					}
					body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 201:
						has_changed = True
						is_failed = False
						meta = {"backup policy "+backuppolicyname+" created."}
				
					else:
						if "is not permitted" in httpreturn.text:

							#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
							#~~~~~ backup feature is not allowed/enabled! -> set only snapshot policy on volume for now! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

							#check if snap policy already assigned on volume!
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2021-10-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()

							#file = open ("/tmp/testfile.txt","w")
							#file.write (httpreturn.text)
							#file.write (returndata["error"]["code"])
							#file.write (str(httpreturn.status_code))
							#file.close()

							try:
								if primarypolicyname not in returndata["properties"]["dataProtection"]["snapshot"]["snapshotPolicyId"]:
									api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2021-10-01"

									body_raw = {
										'properties': {
											'snapshotDirectoryVisible': 'true',
											'dataProtection': {
												'snapshot': {
													'snapshotPolicyId': "/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies/"+primarypolicyname
												}
											}
										}
									}
									body = json.dumps(body_raw)

									headers = {
										'content-type': 'application/json',
										'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
									}
									httpreturn = requests.patch(api_url, data=body, headers=headers)

									if httpreturn.status_code == 202:
										has_changed = True
										is_failed = False
										meta = {"present": "snapshot policy set on volume"}
										return (is_failed, has_changed, meta)
									else:
										has_changed = False
										is_failed = True
										meta = {"snapshot policy set failed - " + httpreturn.text}
										return (is_failed, has_changed, meta)
							except KeyError:
								api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2021-10-01"

								body_raw = {
									'properties': {
										'snapshotDirectoryVisible': 'true',
										'dataProtection': {
											'snapshot': {
												'snapshotPolicyId': "/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies/"+primarypolicyname
											}
										}
									}
								}
								body = json.dumps(body_raw)

								headers = {
									'content-type': 'application/json',
									'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
								}
								httpreturn = requests.patch(api_url, data=body, headers=headers)

								if httpreturn.status_code == 202:
									has_changed = True
									is_failed = False
									meta = {"present": "snapshot policy set on volume"}
									return (is_failed, has_changed, meta)
								else:
									has_changed = False
									is_failed = True
									meta = {"snapshot policy set failed - " + httpreturn.text}
									return (is_failed, has_changed, meta)

						else:
							has_changed = False
							is_failed = True
							meta = {httpreturn.text}
							return (is_failed, has_changed, meta)

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ check if backup is already enabled/set on volume ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2021-10-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				#file = open ("/tmp/testfile.txt","w")
				#file.write (httpreturn.text)
				#file.write (returndata["error"]["code"])
				#file.write (str(httpreturn.status_code))
				#file.close()

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ enable and set "primary5d" and "backupXXd" policies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				
				try:
					if returndata["properties"]["dataProtection"]["backup"]["backupEnabled"] == False:
						
						#get netapp backup vaults
						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/vaults?api-version=2021-10-01"
						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.get(api_url, headers=headers)
						returndata = httpreturn.json()

						backupvault = returndata["value"][0]["id"]
						#file = open ("/tmp/testfile.txt","w")
						#file.write (httpreturn.text)
						#file.write (returndata["value"][0]["id"])
						#file.write (str(httpreturn.status_code))
						#file.close()

						api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"?api-version=2021-10-01"
						body_raw = {
							'properties': {
								'dataProtection': {
									'backup': {
										'backupEnabled': True,
										'backupPolicyId': "/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/backupPolicies/"+backuppolicyname,
										'policyEnforced': True,
										'vaultId': backupvault
									},
									'snapshot': {
										'snapshotPolicyId': "/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/snapshotPolicies/primary5d"
									}
								}
							}
						}
						body = json.dumps(body_raw)

						headers = {
							'content-type': 'application/json',
							'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
						}
						httpreturn = requests.patch(api_url, data=body, headers=headers)

						if httpreturn.status_code == 202:
							has_changed = True
							is_failed = False
							meta = {"present": "backup with policies enabled"}
							return (is_failed, has_changed, meta)
						else:
							has_changed = False
							is_failed = True
							meta = {api_url + "enable backup failed - "+ str(httpreturn.status_code) + httpreturn.text}
							return (is_failed, has_changed, meta)
				except KeyError:
					has_changed = False
					is_failed = False
					meta = {"No backup policies"}
			else:
				has_changed = False
				is_failed = True
				meta = {"Failed to get access token to azure! please check your credentials!"}
		else:
			has_changed = False
			is_failed = True
			tokeninfo = token.json()
			meta = {tokeninfo["error_description"]}
	else:
		has_changed = False
		is_failed = True
		meta = {"Unsupported provider"}

	return (is_failed, has_changed, meta)




def backup(data):

	if data['provider'] == "azure":
		#get first access to azure api and the correct tenant/subscription
		api_url = "https://login.microsoftonline.com/"+data['tenant']+"/oauth2/token"
		body = "grant_type=client_credentials&client_id="+data['client_id']+"&client_secret="+data['secret']+"&resource=https://management.core.windows.net"
		headers = {
			'content-type': 'application/x-www-form-urlencoded'
		}
		token = requests.get(api_url, data=body, headers=headers)
		meta = {token.status_code}

		if token.status_code == 200:

			tokeninfo = token.json()
			
			if tokeninfo.get('token_type') == "Bearer":
				capacitypool = data['sku'].lower()

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ list backup policies ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				#https://docs.microsoft.com/en-us/rest/api/netapp/backup-policies/list?tabs=HTTP
				api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/backupPolicies?api-version=2021-10-01"
				headers = {
					'content-type': 'application/json',
					'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
				}
				httpreturn = requests.get(api_url, headers=headers)
				returndata = httpreturn.json()

				#file = open ("/tmp/testfile.txt","w")
				#file.write (httpreturn.text)
				#file.write (returndata["error"]["code"])
				#file.write (str(httpreturn.status_code))
				#file.close()

				has_changed = False
				is_failed = False
				meta = {"nothing done."}

				if data["retention_days"]:
					backuppolicyname = "backup"+str(data["retention_days"])+"d"
				else:
					backuppolicyname = "backup30d"	#default if not defined
				
				found_backuppolicy = 0

				for policy in returndata["value"]:
					if backuppolicyname in policy["name"]:
						found_backuppolicy = 1

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ if no backup policy with retention name exist, feature is not enabled and do only snap backup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				if found_backuppolicy == 0:

					#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
					#~~~~~ create the volume snapshot ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

					now = datetime.datetime.now()
					mytimenow = now.strftime("%Y%m%d%H%M%S")
					if data['backup_id'] == 0:
						snapname = "ansible-volume-backup-"+mytimenow
					else:
						snapname = "ansible-volume-backup-"+str(data['backup_id'])
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots/"+snapname+"?api-version=2020-08-01"

					body_raw = {
						'location': data['location']
					}
					body = json.dumps(body_raw)

					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)
					#httpreturn = requests.put(api_url, headers=headers)

					if httpreturn.status_code == 201:
						has_changed = True
						is_failed = False
						meta = {"snap created successfully."}
						#check if snap is in provitioningState "Succeeded"
						maxrun = 30
						time.sleep(30) # give Azrue some time to create the snapshot!
						while True:
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots/"+snapname+"?api-version=2020-08-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							maxrun = maxrun + 10
							try:
								if returndata["properties"]["provisioningState"] == "Succeeded":
									break
								else:
									time.sleep(10)
							except KeyError:
								time.sleep(10)
							#return failure if snap takes longer than 5 min!
							maxrun = maxrun + 10
							if maxrun == 300:
								has_changed = False
								is_failed = True
								meta = {"Error: Runtime of snap creation was longer than 5 min. Please re-run the job!"}
								return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						#meta = {httpreturn.status_code}
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

					#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
					#~~~~~ ensure snapshot retention ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots?api-version=2020-08-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					returndata = httpreturn.json()

					#file = open ("/tmp/testfile.txt","w")
					#file.write (returndata["value"][0]["properties"]["name"])
					#file.write (returndata["value"][0]["properties"]["created"])

					#meta = {httpreturn.text}
					#meta = {returndata[0]["properties"]["name"]}
					for snap in returndata["value"]:
						x_days_ago = datetime.datetime.now()-datetime.timedelta(data['retention_days'])
						returntime = datetime.datetime.strptime(snap["properties"]["created"], "%Y-%m-%dT%H:%M:%SZ")
						if returntime < x_days_ago:
							snapname = snap["name"].split('/')[3]

							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/snapshots/"+snapname+"?api-version=2020-08-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.delete(api_url, headers=headers)

				#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#~~~~~ if backup policy exist, feature is enabled so run ANF backup ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

				else:
					now = datetime.datetime.now()
					mytimenow = now.strftime("%Y%m%d%H%M%S")

					if data['backup_id'] == 0:
						snapname = "ansible-volume-backup-"+mytimenow
					else:
						snapname = "ansible-volume-backup-"+str(data['backup_id'])

					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/backups/"+snapname+"?api-version=2021-02-01"
					body_raw = {
						'location': data['location'],
						'properties': {
							'label': ''
						}
					}
					body = json.dumps(body_raw)
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.put(api_url, data=body, headers=headers)

					if httpreturn.status_code == 201:
						has_changed = True
						is_failed = False
						meta = {"Backup created successfully."}
						#check if backup is in provitioningState "Succeeded"
						maxrun = 30
						time.sleep(30) # give Azrue some time to create the snapshot!
						while True:
							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/backups/"+snapname+"?api-version=2021-10-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.get(api_url, headers=headers)
							returndata = httpreturn.json()
							maxrun = maxrun + 10
							try:
								if returndata["properties"]["provisioningState"] == "Succeeded":
									break
								else:
									time.sleep(10)
							except KeyError:
								time.sleep(10)
							#return failure if snap takes longer than 5 min!
							maxrun = maxrun + 10
							if maxrun == 300:
								has_changed = False
								is_failed = True
								meta = {"Error: Runtime of backup creation was longer than 5 min. Please re-run the job or ask a devops engineer!"}
								return (is_failed, has_changed, meta)
					else:
						has_changed = False
						is_failed = True
						meta = {httpreturn.text}
						return (is_failed, has_changed, meta)

					#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
					#~~~~~ ensure backup retention ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
					api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/backups?api-version=2021-10-01"
					headers = {
						'content-type': 'application/json',
						'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
					}
					httpreturn = requests.get(api_url, headers=headers)
					returndata = httpreturn.json()

					#file = open ("/tmp/testfile.txt","w")
					#file.write (returndata["value"][0]["properties"]["name"])
					#file.write (returndata["value"][0]["properties"]["created"])

					#meta = {httpreturn.text}
					#meta = {returndata[0]["properties"]["name"]}
					for snap in returndata["value"]:
						x_days_ago = datetime.datetime.now()-datetime.timedelta(data['retention_days'])
						returntime = datetime.datetime.strptime(snap["properties"]["created"], "%Y-%m-%dT%H:%M:%SZ")
						if returntime < x_days_ago:
							snapname = snap["name"].split('/')[3]

							api_url = "https://management.azure.com/subscriptions/"+data['subscription_id']+"/resourceGroups/"+data['resource_group']+"/providers/Microsoft.NetApp/netAppAccounts/"+data['accountname']+"/capacityPools/"+capacitypool+"/volumes/"+data['volname']+"/backups/"+snapname+"?api-version=2021-10-01"
							headers = {
								'content-type': 'application/json',
								'Authorization': tokeninfo['token_type']+' '+tokeninfo['access_token']
							}
							httpreturn = requests.delete(api_url, headers=headers)

			else:
				has_changed = False
				is_failed = True
				meta = {"Failed to get access token to azure! please check your credentials!"}
		else:
			has_changed = False
			is_failed = True
			tokeninfo = token.json()
			meta = {tokeninfo["error_description"]}
	else:
		has_changed = False
		is_failed = True
		meta = {"Unsupported provider"}
			
	return (is_failed, has_changed, meta)



def restore(data=None):
	has_changed = False
	is_failed = False
	meta = {"restore": "not yet implemented"}
	return (is_failed, has_changed, meta)



def main():

	fields = {
		"provider": {
			"required": False, 
			"default": "azure",
			"choices": ["azure"],
			"type": "str"
		},
		"tenant": {"required": True, "type": "str"},
		"subscription_id": {"required": True, "type": "str"},
		"client_id": {"required": True, "type": "str"},
		"secret": {"required": True, "type": "str"},
		"resource_group": {"required": True, "type": "str"},
		"location": {
			"required": False, 
			"default": "westeurope",
			"type": "str"
		},
		"accountname": {"required": True, "type": "str"},
		"sku": {
			"required": False, 
			"default": "Premium",
			"type": "str"
		},
		"volname": {"required": True, "type": "str"},
		"retention_days": {
			"required": False,
			"default": 30,
			"type": "int"
		},
		"state": {
			"required": False, 
			"default": "backup",
			"choices": ["backup", "restore", "setup"],
			"type": "str"
		},
		"backup_id": {
			"required": False,
			"default": 0,
			"type": "int"
		},
	}

	choice_map = {
		"setup": setup,
		"backup": backup,
		"restore": restore,
	}

	module = AnsibleModule(argument_spec=fields)
	is_failed, has_changed, result = choice_map.get(module.params["state"])(module.params)
	module.exit_json(failed=is_failed, changed=has_changed, msg=result)



if __name__ == '__main__':
	main()
